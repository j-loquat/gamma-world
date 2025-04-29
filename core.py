# core.py
import random
import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import Counter

from models import (
    Attributes, CharacterType, AttributeRollMethod, MutationSelectionMethod,
    MutationType, Mutation, MutationSlot, IntermediateCharacterState, Character,
    GenerateCharacterRequest, FinalizeMutationsRequest
)
import utils
import config

log = logging.getLogger(__name__)

# --- Attribute and HP Generation ---

def roll_attributes(method: AttributeRollMethod) -> Attributes:
    """Generates the six core attributes based on the chosen method."""
    log.info(f"Rolling attributes using method: {method.value}")
    roll_func = utils.roll_dice if method == AttributeRollMethod.STANDARD_3D6 else utils.roll_4d6_drop_lowest
    args = (3, 6) if method == AttributeRollMethod.STANDARD_3D6 else ()

    attrs_dict = {
        "mentalStrength": roll_func(*args),
        "intelligence": roll_func(*args),
        "dexterity": roll_func(*args),
        "charisma": roll_func(*args),
        "constitution": roll_func(*args),
        "physicalStrength": roll_func(*args)
    }
    # Use populate_by_name=True in model_config to handle aliases
    attrs = Attributes(**attrs_dict)
    log.info(f"Generated attributes: MS={attrs.mental_strength}, IN={attrs.intelligence}, DX={attrs.dexterity}, CH={attrs.charisma}, CN={attrs.constitution}, PS={attrs.physical_strength}")
    return attrs

def calculate_hp(constitution: int) -> int:
    """Calculates starting Hit Points by rolling d6 equal to Constitution score."""
    if constitution < 1:
        log.warning(f"Constitution is {constitution}, cannot roll HP. Defaulting to 1.")
        return 1
    hp = utils.roll_dice(constitution, 6)
    log.info(f"Calculated HP based on CN {constitution}: {hp} (rolled {constitution}d6)")
    return hp

# --- Mutation Handling ---

def get_mutation_by_roll(roll: int, mutations_pool: List[Dict[str, Any]], character_type: CharacterType) -> Optional[Dict[str, Any]]:
    """Finds a mutation dict from the list based on a d100 roll and character type."""
    percentage_key = 'humanPercentage' if character_type in [CharacterType.PSH, CharacterType.HUMANOID] else 'animalPercentage'
    for mutation_dict in mutations_pool:
        min_val, max_val = utils.parse_percentage_range(mutation_dict.get(percentage_key, ''))
        if min_val <= roll <= max_val:
            return mutation_dict
    log.warning(f"No mutation found for roll {roll}% ({character_type.value}) in the provided pool.")
    return None

def select_random_mutation(
    mutations_pool: List[Dict[str, Any]],
    allow_defect: bool = True,
    exclude_names: Optional[Set[str]] = None
) -> Optional[Mutation]:
    """
    Selects a random valid mutation dict, converts to Mutation model,
    optionally excluding defects, special roll results, and names from the exclude_names set.
    """
    if exclude_names is None:
        exclude_names = set()

    valid_mutations = [
        m for m in mutations_pool
        if m.get('number') is not None # Exclude special roll results like 'Pick Any'
        and (allow_defect or not m.get('isDefect', False)) # Handle defect allowance
        and m.get('name') not in exclude_names # Exclude already acquired mutations
    ]

    if not valid_mutations:
        log.warning(f"No valid mutations found to select from (allow_defect={allow_defect}, excluding {len(exclude_names)} names).")
        return None

    chosen_dict = random.choice(valid_mutations)
    try:
        return Mutation(**chosen_dict) # Convert dict back to Pydantic model
    except Exception as e:
        log.error(f"Error converting chosen dict to Mutation model: {chosen_dict}. Error: {e}", exc_info=True)
        return None # Or raise a specific error

def get_random_defect(mutations_pool: List[Dict[str, Any]], exclude_names: Optional[Set[str]] = None) -> Optional[Mutation]:
    """Selects a random defect mutation dict from the list, converts to Mutation model, excluding names from exclude_names."""
    if exclude_names is None:
        exclude_names = set()

    defects = [
        m for m in mutations_pool
        if m.get('isDefect', False)
        and m.get('number') is not None # Ensure it's a real defect, not a special roll
        and m.get('name') not in exclude_names
    ]

    if not defects:
        log.warning(f"No valid defects found to select from (excluding {len(exclude_names)} names).")
        return None

    chosen_dict = random.choice(defects)
    try:
        return Mutation(**chosen_dict) # Convert dict back to Pydantic model
    except Exception as e:
        log.error(f"Error converting chosen defect dict to Mutation model: {chosen_dict}. Error: {e}", exc_info=True)
        return None

def get_selectable_mutations_list(mutation_pool: List[Dict[str, Any]]) -> List[Mutation]:
    """Filters a mutation pool to get selectable, non-defect mutations."""
    selectable = []
    for m_dict in mutation_pool:
        # Check if it's a real mutation (has a number) AND is NOT a defect
        if m_dict.get('number') is not None and not m_dict.get('isDefect', False):
            try:
                selectable.append(Mutation(**m_dict))
            except Exception as e:
                 log.warning(f"Skipping mutation due to parsing error: {m_dict.get('name', 'UNKNOWN')}. Error: {e}")
    return selectable


# --- Character Generation Steps ---

def _determine_initial_state(gen_request: GenerateCharacterRequest) -> Tuple[Character, List[str]] | Tuple[IntermediateCharacterState, List[str]]:
    """Handles Phases 1, 2, 4 and prepares for Phase 3 (Mutations)."""
    log_list = [f"Starting character generation for type: {gen_request.character_type.value}"]
    char_type = gen_request.character_type
    base_animal = gen_request.base_animal_species if char_type == CharacterType.MUTATED_ANIMAL else None

    if char_type == CharacterType.MUTATED_ANIMAL:
        log_list.append(f"Selected Mutated Animal ({base_animal}). NOTE: Referee adjudication needed for speech/manipulation capabilities.")
        log.info(f"Mutated Animal ({base_animal}): Referee adjudication needed.")

    # Phase 2: Attributes
    attributes = roll_attributes(gen_request.attribute_method)
    log_list.append(f"Rolled attributes ({gen_request.attribute_method.value}): MS={attributes.mental_strength}, IN={attributes.intelligence}, DX={attributes.dexterity}, CH={attributes.charisma}, CN={attributes.constitution}, PS={attributes.physical_strength}")

    # Apply PSH Bonus
    if char_type == CharacterType.PSH:
        original_charisma = attributes.charisma
        attributes.charisma = min(attributes.charisma + 3, 18)
        if attributes.charisma != original_charisma:
            log_list.append(f"Applied PSH bonus: Charisma increased from {original_charisma} to {attributes.charisma}.")
            log.info(f"PSH Charisma bonus applied: {original_charisma} -> {attributes.charisma}")

    # Phase 4: HP
    hp = calculate_hp(attributes.constitution)
    log_list.append(f"Calculated starting Hit Points: {hp} (rolled {attributes.constitution}d6).")

    # Early Exit for PSH
    if char_type == CharacterType.PSH:
        log_list.append("Character is Pure Strain Human. Skipping mutation phase.")
        log.info("PSH: Skipping mutations, returning final character.")
        final_character = Character(
            name=gen_request.name,
            characterType=char_type, # Use alias for Pydantic
            baseAnimalSpecies=base_animal, # Use alias
            attributes=attributes,
            hitPoints=hp, # Use alias
            physicalMutations=[], # Use alias
            mentalMutations=[], # Use alias
            generationLog=log_list # Use alias
        )
        return final_character, log_list # Return final character

    # Prepare Intermediate State for Non-PSH
    intermediate_state = IntermediateCharacterState(
        name=gen_request.name,
        characterType=char_type, # Alias
        baseAnimalSpecies=base_animal, # Alias
        attributes=attributes,
        hitPoints=hp, # Alias
        mutationSlots=[], # Alias - will be populated next
        assignedMutationNames=[], # Alias
        generationLog=log_list, # Alias
        originalRequest=gen_request # Alias
    )
    return intermediate_state, log_list


def _process_random_roll_slot(
    type_slot_index: int,
    mutation_type: MutationType,
    mutation_pool: List[Dict[str, Any]],
    character_type: CharacterType,
    acquired_names: Set[str],
    log_list: List[str]
) -> MutationSlot:
    """Helper for Method 1: Processes a single mutation slot roll."""
    internal_index = type_slot_index - 1
    slot_id = f"{mutation_type.value.lower()}-{internal_index}"
    roll = utils.roll_dice(1, 100)
    mutation_dict = get_mutation_by_roll(roll, mutation_pool, character_type)
    log_msg_base = f"{mutation_type.value} Slot {type_slot_index} (Roll {roll}%): "

    if not mutation_dict:
        log_list.append(log_msg_base + "No mutation found for this roll. Treating as Player Choice.")
        log.warning(log_msg_base + "No mutation found! Player Choice required.")
        return MutationSlot(slotId=slot_id, mutationType=mutation_type, typeIndex=type_slot_index, isChoiceRequired=True) # Aliases

    potential_mutation_name = mutation_dict.get("name", "UNKNOWN")
    log_msg_base += f"{potential_mutation_name}"
    final_mutation: Optional[Mutation] = None
    is_choice = False
    is_special_roll = mutation_dict.get("number") is None

    if is_special_roll:
        allow_defect_reroll = True
        is_good_roll = False
        # Determine special roll type based on percentage ranges
        if mutation_type == MutationType.PHYSICAL:
            if 91 <= roll <= 94: allow_defect_reroll = False; is_good_roll = True; log_msg_base += " -> Rerolling (Good)"
            elif 95 <= roll <= 100: log_msg_base += " -> Player Choice (Pick Any)"; is_choice = True
        elif mutation_type == MutationType.MENTAL:
            if 96 <= roll <= 99: allow_defect_reroll = False; is_good_roll = True; log_msg_base += " -> Rerolling (Good)"
            elif roll == 100: log_msg_base += " -> Player Choice (Pick Any)"; is_choice = True

        if not is_choice and is_good_roll: # Handle "Roll Good" reroll
            attempts = 0
            while attempts < config.MAX_REROLL_ATTEMPTS:
                attempts += 1
                rerolled_mutation = select_random_mutation(mutation_pool, allow_defect=allow_defect_reroll, exclude_names=acquired_names)
                if rerolled_mutation and rerolled_mutation.name not in acquired_names:
                    final_mutation = rerolled_mutation
                    log_msg_base += f": {final_mutation.name}"
                    if attempts > 1: log_msg_base += f" (Unique found after {attempts} attempts)"
                    break
                elif rerolled_mutation:
                    log_list.append(f"   - Reroll attempt {attempts} got duplicate '{rerolled_mutation.name}'. Trying again...")
                    log.debug(f"   - Reroll attempt {attempts} duplicate '{rerolled_mutation.name}'.")
                else:
                    log_list.append(f"   - Reroll attempt {attempts} failed to find any valid mutation.")
                    log.warning(f"   - Reroll attempt {attempts} failed.")
                    break
            if not final_mutation:
                log_list.append(log_msg_base + " -> Failed to find unique Good mutation. Treating as Player Choice.")
                log.warning(log_msg_base + " -> Failed Good reroll. Player Choice required.")
                is_choice = True
    else: # Handle Normal Roll
        try:
            potential_mutation_obj = Mutation(**mutation_dict)
            if potential_mutation_obj.name not in acquired_names:
                final_mutation = potential_mutation_obj
            else: # Duplicate found on initial roll
                log_list.append(log_msg_base + f" -> Duplicate '{potential_mutation_obj.name}'. Treating as Player Choice.")
                log.warning(log_msg_base + f" -> Duplicate '{potential_mutation_obj.name}'. Player Choice required.")
                is_choice = True
        except Exception as e:
            log_list.append(log_msg_base + f" -> Error parsing mutation. Treating as Player Choice. Error: {e}")
            log.error(log_msg_base + f" -> Error parsing. Player Choice required. Error: {e}", exc_info=True)
            is_choice = True

    # Finalize Slot
    if is_choice:
        log_list.append(log_msg_base + " -> Requires Player Selection.")
        log.info(log_msg_base + " -> Requires Player Selection.")
        return MutationSlot(slotId=slot_id, mutationType=mutation_type, typeIndex=type_slot_index, isChoiceRequired=True) # Aliases
    elif final_mutation:
        log_msg_final = log_msg_base
        if final_mutation.isDefect: log_msg_final += " (Defect)"
        log_list.append(log_msg_final)
        log.info(log_msg_final)
        acquired_names.add(final_mutation.name)
        # assigned_mutation_names_list.append(final_mutation.name) # This is handled in the calling function
        return MutationSlot(slotId=slot_id, mutationType=mutation_type, typeIndex=type_slot_index, isChoiceRequired=False, assignedMutation=final_mutation) # Aliases
    else: # Fallback
         log_list.append(log_msg_base + " -> Internal error determining slot. Treating as Player Choice.")
         log.error(log_msg_base + " -> Internal error. Player Choice required.")
         return MutationSlot(slotId=slot_id, mutationType=mutation_type, typeIndex=type_slot_index, isChoiceRequired=True) # Aliases


def _determine_mutation_slots_method1(
    intermediate_state: IntermediateCharacterState,
    num_physical: int,
    num_mental: int,
    log_list: List[str]
) -> Tuple[List[MutationSlot], List[str]]:
    """Determines mutation slots using Method 1 (Random Roll)."""
    log_list.append("Using Mutation Method 1: Random Roll.")
    log.info("Determining mutation slots using Random Roll (Method 1)...")
    mutation_slots: List[MutationSlot] = []
    acquired_physical_names: Set[str] = set()
    acquired_mental_names: Set[str] = set()
    assigned_names: List[str] = []

    # Process Physical Slots
    for i in range(num_physical):
        slot = _process_random_roll_slot(i + 1, MutationType.PHYSICAL, config.PHYSICAL_MUTATIONS_DATA, intermediate_state.character_type, acquired_physical_names, log_list)
        mutation_slots.append(slot)
        if slot.assigned_mutation:
            assigned_names.append(slot.assigned_mutation.name)

    # Process Mental Slots
    for i in range(num_mental):
        slot = _process_random_roll_slot(i + 1, MutationType.MENTAL, config.MENTAL_MUTATIONS_DATA, intermediate_state.character_type, acquired_mental_names, log_list)
        mutation_slots.append(slot)
        if slot.assigned_mutation:
            assigned_names.append(slot.assigned_mutation.name)

    return mutation_slots, assigned_names


def _determine_mutation_slots_method2(
    intermediate_state: IntermediateCharacterState,
    num_physical_roll: int,
    num_mental_roll: int,
    log_list: List[str]
) -> Tuple[List[MutationSlot], List[str]]:
    """Determines mutation slots using Method 2 (Player Choice + Defect Assignment)."""
    log_list.append("Using Mutation Method 2: Player Choice + Referee Defect Assignment.")
    log.info("Determining mutation slots using Player Choice (Method 2)...")
    mutation_slots: List[MutationSlot] = []
    acquired_physical_names: Set[str] = set()
    acquired_mental_names: Set[str] = set()
    assigned_names: List[str] = []

    num_physical_defects = 0
    num_mental_defects = 0

    # Defect Assignment Rules
    if num_physical_roll >= 3 and num_mental_roll >= 3:
        num_physical_defects = 1; num_mental_defects = 1; log_list.append("Assigning 1 Physical Defect and 1 Mental Defect (rolls >= 3).")
    elif num_physical_roll >= 3:
        num_physical_defects = 1; log_list.append("Assigning 1 Physical Defect (physical roll >= 3).")
    elif num_mental_roll >= 3:
        num_mental_defects = 1; log_list.append("Assigning 1 Mental Defect (mental roll >= 3).")
    elif num_physical_roll == 2 and num_mental_roll == 2:
        if random.choice([True, False]): num_physical_defects = 1; log_list.append("Assigning 1 Physical Defect (rolls == 2, random choice).")
        else: num_mental_defects = 1; log_list.append("Assigning 1 Mental Defect (rolls == 2, random choice).")
    else: log_list.append("No defects assigned based on roll counts.")
    log.info(f"Defects to assign: {num_physical_defects} Physical, {num_mental_defects} Mental.")

    # --- Helper for Method 2 Defect Assignment ---
    def assign_defect_slot(
        type_slot_index: int,
        mutation_type: MutationType,
        mutation_pool: List[Dict[str, Any]],
        num_defects_to_assign: int,
        assigned_defect_count: int,
        acquired_names: Set[str],
        assigned_names_list: List[str],
        log_list_ref: List[str]
    ) -> Tuple[Optional[MutationSlot], int]:
        slot_id = f"{mutation_type.value.lower()}-{type_slot_index - 1}"
        if assigned_defect_count < num_defects_to_assign:
            attempts = 0
            defect_to_assign: Optional[Mutation] = None
            while attempts < config.MAX_REROLL_ATTEMPTS:
                attempts += 1
                defect = get_random_defect(mutation_pool, exclude_names=acquired_names)
                if defect and defect.name not in acquired_names:
                    defect_to_assign = defect
                    acquired_names.add(defect.name)
                    assigned_names_list.append(defect.name)
                    log_list_ref.append(f"{mutation_type.value} Slot {type_slot_index}: Assigned Defect: {defect.name} (Attempt {attempts})")
                    log.info(f"{mutation_type.value} Slot {type_slot_index}: Assigned Defect: {defect.name}")
                    break
                elif defect: log_list_ref.append(f"   - Defect assign attempt {attempts} got duplicate '{defect.name}'. Trying again..."); log.debug(f"   - Defect assign duplicate '{defect.name}'.")
                else: log_list_ref.append(f"   - Defect assign attempt {attempts} failed to find any valid defect."); log.warning(f"   - Defect assign attempt {attempts} failed."); break

            if defect_to_assign:
                return MutationSlot(slotId=slot_id, mutationType=mutation_type, typeIndex=type_slot_index, isChoiceRequired=False, assignedMutation=defect_to_assign, isDefectSlot=True), assigned_defect_count + 1 # Aliases
            else:
                log_list_ref.append(f"{mutation_type.value} Slot {type_slot_index}: Failed to assign unique defect. Requires Player Choice (Defect).")
                log.error(f"{mutation_type.value} Slot {type_slot_index}: Failed defect assign. Player Choice (Defect) required but unsupported.")
                # NOTE: Frontend doesn't currently support choosing defects. Mark as choice required but also defect.
                return MutationSlot(slotId=slot_id, mutationType=mutation_type, typeIndex=type_slot_index, isChoiceRequired=True, isDefectSlot=True), assigned_defect_count # Aliases
        else: # Not a defect slot, requires player choice of non-defect
            log_list_ref.append(f"{mutation_type.value} Slot {type_slot_index}: Requires Player Choice (Non-Defect).")
            log.info(f"{mutation_type.value} Slot {type_slot_index}: Requires Player Choice (Non-Defect).")
            return MutationSlot(slotId=slot_id, mutationType=mutation_type, typeIndex=type_slot_index, isChoiceRequired=True, isDefectSlot=False), assigned_defect_count # Aliases
    # --- End Helper ---

    # Assign Physical Slots
    current_physical_defects = 0
    for i in range(num_physical_roll):
        slot, current_physical_defects = assign_defect_slot(
            i + 1, MutationType.PHYSICAL, config.PHYSICAL_MUTATIONS_DATA,
            num_physical_defects, current_physical_defects,
            acquired_physical_names, assigned_names, log_list
        )
        if slot: mutation_slots.append(slot)

    # Assign Mental Slots
    current_mental_defects = 0
    for i in range(num_mental_roll):
        slot, current_mental_defects = assign_defect_slot(
            i + 1, MutationType.MENTAL, config.MENTAL_MUTATIONS_DATA,
            num_mental_defects, current_mental_defects,
            acquired_mental_names, assigned_names, log_list
        )
        if slot: mutation_slots.append(slot)

    return mutation_slots, assigned_names


def start_character_generation(gen_request: GenerateCharacterRequest) -> Tuple[Optional[Character], Optional[IntermediateCharacterState]]:
    """
    Main entry point for character generation.
    Returns either a final Character or an IntermediateCharacterState.
    """
    # Phase 1, 2, 4
    initial_result, log_list = _determine_initial_state(gen_request)

    if isinstance(initial_result, Character):
        # PSH character, generation complete
        return initial_result, None

    # Must be IntermediateCharacterState for non-PSH
    intermediate_state = initial_result
    intermediate_state.generation_log = log_list # Update log

    # Phase 3: Determine Mutations (Non-PSH only)
    if not config.PHYSICAL_MUTATIONS_DATA or not config.MENTAL_MUTATIONS_DATA:
         log.critical("Mutation data not loaded. Cannot generate mutations.")
         raise RuntimeError("Mutation data not loaded. Cannot generate mutations.") # Internal error

    num_physical_roll = utils.roll_dice(1, 4)
    num_mental_roll = utils.roll_dice(1, 4)
    log_list.append(f"Rolled for number of mutations: {num_physical_roll} Physical, {num_mental_roll} Mental.")
    log.info(f"Mutation counts rolled: {num_physical_roll} Physical, {num_mental_roll} Mental")

    # Determine slots based on method
    if gen_request.mutation_method == MutationSelectionMethod.RANDOM_ROLL:
        mutation_slots, assigned_names = _determine_mutation_slots_method1(
            intermediate_state, num_physical_roll, num_mental_roll, log_list
        )
    elif gen_request.mutation_method == MutationSelectionMethod.PLAYER_CHOICE_DEFECT_ASSIGN:
        mutation_slots, assigned_names = _determine_mutation_slots_method2(
            intermediate_state, num_physical_roll, num_mental_roll, log_list
        )
    else:
        # Should not happen with Enum validation, but good practice
        log.error(f"Unknown mutation method: {gen_request.mutation_method}")
        raise ValueError(f"Invalid mutation selection method: {gen_request.mutation_method}")

    intermediate_state.mutation_slots = mutation_slots
    intermediate_state.assigned_mutation_names = assigned_names
    intermediate_state.generation_log = log_list # Update log again

    # Phase 5: Final Review (Hopeless Character Check - Log only)
    # Use internal attribute names here
    is_potentially_hopeless = sum(1 for stat in intermediate_state.attributes.model_dump().values() if stat <= 8) >= 4
    if is_potentially_hopeless:
        log_list.append("NOTE: Character has multiple low attributes. Referee discretion advised for 'Hopeless Character' check.")
        log.warning("Character has multiple low attributes. Consider 'Hopeless Character' check.")

    # Check if any slots actually require choice
    needs_selection = any(slot.is_choice_required for slot in mutation_slots)

    if not needs_selection:
        # If no selection is needed (e.g., all assigned defects or Method 1 resulted in no choices)
        log_list.append("All mutation slots determined randomly or assigned. Finalizing character directly.")
        log.info("All mutation slots determined. Finalizing character directly.")
        final_physical = [slot.assigned_mutation for slot in mutation_slots if slot.mutation_type == MutationType.PHYSICAL and slot.assigned_mutation]
        final_mental = [slot.assigned_mutation for slot in mutation_slots if slot.mutation_type == MutationType.MENTAL and slot.assigned_mutation]
        final_character = Character(
            name=intermediate_state.name,
            characterType=intermediate_state.character_type, # Alias
            baseAnimalSpecies=intermediate_state.base_animal_species, # Alias
            attributes=intermediate_state.attributes,
            hitPoints=intermediate_state.hit_points, # Alias
            physicalMutations=final_physical, # Alias
            mentalMutations=final_mental, # Alias
            generationLog=log_list # Alias
        )
        return final_character, None
    else:
        # Return Intermediate State for selection
        log.info("Character generation paused. Returning intermediate state for mutation selection.")
        return None, intermediate_state


def finalize_character_with_selections(finalize_request: FinalizeMutationsRequest) -> Character:
    """Finalizes character creation using the selected mutations."""
    log.info("Received request to finalize mutations.")
    state = finalize_request.intermediate_state
    selections = finalize_request.selected_mutations # slot_id (camelCase) -> name
    log_list = state.generation_log[:] # Copy log
    log_list.append("Finalizing mutation selections...")

    final_physical_mutations: List[Mutation] = []
    final_mental_mutations: List[Mutation] = []
    # Combine pre-assigned names and user selections for final uniqueness check
    # Use internal attribute names from state
    combined_names = set(state.assigned_mutation_names)
    user_selected_names_list = list(selections.values())

    # --- Check for duplicates within user selections ---
    selection_counts = Counter(user_selected_names_list)
    duplicates_in_selection = {name: count for name, count in selection_counts.items() if count > 1}
    if duplicates_in_selection:
        duplicate_details = []
        duplicate_slots_map = {} # Store slot_id -> name for error response
        for slot_id, name in selections.items():
            if name in duplicates_in_selection:
                 # Use internal attribute names from state
                 slot_obj = next((s for s in state.mutation_slots if s.slot_id == slot_id), None)
                 if slot_obj:
                     duplicate_details.append(f"{slot_obj.mutation_type.value} Slot {slot_obj.type_index} ('{name}')")
                     duplicate_slots_map[slot_id] = name

        error_msg = f"Duplicate mutations selected: {', '.join(duplicates_in_selection.keys())}. Affected slots: {'; '.join(duplicate_details)}. Please make unique selections."
        log_list.append(f"Error: {error_msg}")
        log.error(f"Duplicate selection error: {error_msg}")
        # Raise a specific error type to be caught by the route handler
        raise ValueError(error_msg, duplicate_slots_map) # Pass duplicate info

    # Add already assigned mutations first
    # Use internal attribute names from state
    for slot in state.mutation_slots:
        if slot.assigned_mutation:
            target_list = final_physical_mutations if slot.mutation_type == MutationType.PHYSICAL else final_mental_mutations
            target_list.append(slot.assigned_mutation)

    # Process user selections
    # Use internal attribute names from state
    for slot in state.mutation_slots:
        if slot.is_choice_required:
            # Check if this slot requires a defect choice (currently unsupported by frontend)
            if slot.is_defect_slot:
                 log_list.append(f"Warning: Skipping finalization for defect choice slot {slot.slot_id} ({slot.mutation_type.value} Slot {slot.type_index}) as frontend selection is not implemented.")
                 log.warning(f"Skipping finalization for defect choice slot {slot.slot_id} - frontend selection not implemented.")
                 if slot.slot_id in selections:
                     err_msg = f"Received unexpected selection for required defect slot {slot.slot_id}."
                     log_list.append(f"Error: {err_msg}")
                     log.error(err_msg)
                     raise ValueError(f"Cannot process selection for required defect slot {slot.mutation_type.value} Slot {slot.type_index}.")
                 continue # Skip this slot

            # Process normal non-defect choices
            selected_name = selections.get(slot.slot_id) # slot_id is camelCase from request
            if not selected_name:
                err_msg = f"Missing mutation selection for {slot.mutation_type.value} Slot {slot.type_index} (ID: {slot.slot_id})"
                log_list.append(f"Error: {err_msg}")
                log.error(err_msg)
                raise ValueError(err_msg)

            # Check if this selection duplicates a pre-assigned one
            if selected_name in state.assigned_mutation_names:
                 err_msg = f"Selection '{selected_name}' for {slot.mutation_type.value} Slot {slot.type_index} conflicts with a pre-assigned mutation."
                 log_list.append(f"Error: {err_msg}")
                 log.error(err_msg)
                 raise ValueError(err_msg)

            # Check if this selection duplicates *another user selection* (already checked by Counter, but good safeguard)
            if selected_name in combined_names:
                 err_msg = f"Duplicate mutation selected: '{selected_name}' (Slot {slot.slot_id})."
                 log_list.append(f"Error: {err_msg}")
                 log.error(err_msg)
                 # This should ideally be caught by the 409 error earlier, but raise here too
                 raise ValueError(err_msg) # Raise generic ValueError

            # Find the selected mutation in the appropriate global list
            mutation_pool = config.PHYSICAL_MUTATIONS_DATA if slot.mutation_type == MutationType.PHYSICAL else config.MENTAL_MUTATIONS_DATA
            found_mutation_dict = next((m for m in mutation_pool if m.get("name") == selected_name), None)

            if not found_mutation_dict:
                err_msg = f"Invalid mutation selected: '{selected_name}' (Slot {slot.slot_id})"
                log_list.append(f"Error: {err_msg}")
                log.error(err_msg)
                raise ValueError(err_msg)

            try:
                selected_mutation = Mutation(**found_mutation_dict)
            except Exception as e:
                 err_msg = f"Error processing selected mutation: '{selected_name}' (Slot {slot.slot_id})"
                 log_list.append(f"Error: {err_msg}. Details: {e}")
                 log.error(f"{err_msg}. Details: {e}", exc_info=True)
                 raise RuntimeError(err_msg) from e # Internal processing error

            # Validate selection type (defect vs non-defect) - Redundant check as defect slots are skipped above, but safe
            if selected_mutation.isDefect and not slot.is_defect_slot:
                 err_msg = f"Cannot select defect '{selected_name}' for non-defect slot {slot.mutation_type.value} Slot {slot.type_index}."
                 log_list.append(f"Error: {err_msg}")
                 log.error(err_msg)
                 raise ValueError(err_msg)

            target_list = final_physical_mutations if slot.mutation_type == MutationType.PHYSICAL else final_mental_mutations
            target_list.append(selected_mutation)
            combined_names.add(selected_mutation.name) # Add to set for subsequent checks
            log_list.append(f"{slot.mutation_type.value} Slot {slot.type_index}: Finalized selection: {selected_mutation.name}")
            log.info(f"{slot.mutation_type.value} Slot {slot.type_index}: Finalized selection: {selected_mutation.name}")

    # Construct final character object using aliases for Pydantic
    final_character = Character(
        name=state.name,
        characterType=state.character_type,
        baseAnimalSpecies=state.base_animal_species,
        attributes=state.attributes,
        hitPoints=state.hit_points,
        physicalMutations=final_physical_mutations,
        mentalMutations=final_mental_mutations,
        generationLog=log_list
    )

    log.info("Character finalization complete.")
    return final_character