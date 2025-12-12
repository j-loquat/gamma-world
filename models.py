# models.py
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --- Enums ---


class CharacterType(str, Enum):
    """Enumeration for the different character types."""

    PSH = "Pure Strain Human"
    HUMANOID = "Humanoid"
    MUTATED_ANIMAL = "Mutated Animal"


class AttributeRollMethod(str, Enum):
    """Enumeration for attribute rolling methods."""

    STANDARD_3D6 = "Standard (3d6)"
    HEROIC_4D6_DROP_LOWEST = "Heroic (4d6 drop lowest)"


class MutationSelectionMethod(str, Enum):
    """Enumeration for mutation selection methods."""

    RANDOM_ROLL = "Random Roll (Method 1)"
    PLAYER_CHOICE_DEFECT_ASSIGN = "Player Choice + Referee Defect Assignment (Method 2)"


class MutationType(str, Enum):
    PHYSICAL = "Physical"
    MENTAL = "Mental"


# --- Core Models ---


class MutationTableEntry(BaseModel):
    # Making fields optional as they vary between tables
    dieRoll: Optional[str] = None
    result: Optional[str] = None
    distanceTraveled: Optional[str] = None
    percentChance: Optional[str] = None
    aspect: Optional[str] = None
    prevailing: Optional[str] = None
    change: Optional[str] = None
    # Add fields from other tables if needed, e.g., Charisma Table
    charismaScore: Optional[Union[int, str]] = Field(None, alias="Charisma Score")
    maxFollowers: Optional[Union[int, str]] = Field(None, alias="Maximum No. of Followers")
    moraleAdj: Optional[Union[int, str]] = Field(None, alias="Morale Adjustment")
    reactionAdj: Optional[Union[int, str]] = Field(None, alias="Reaction Adjustment")
    diceScore: Optional[str] = Field(None, alias="Dice Score")
    reaction: Optional[str] = Field(None, alias="Reaction")
    playerCharType: Optional[str] = Field(None, alias="Player Character Type")
    npcPsh: Optional[str] = Field(None, alias="Non-Player Character Type: PSH")
    npcHumanoid: Optional[str] = Field(None, alias="Non-Player Character Type: Humanoid")
    npcMutAnimal: Optional[str] = Field(None, alias="Non-Player Character Type: Mutated Animal")

    model_config = ConfigDict(populate_by_name=True)


class MutationTable(BaseModel):
    title: str
    columns: List[str]
    rows: List[Dict[str, Any]]  # Keep as dict initially, parse later if needed
    notes: Optional[str] = None


class Mutation(BaseModel):
    number: Optional[int] = None
    humanPercentage: str
    name: str
    animalPercentage: str
    isDefect: bool
    description: str
    hasTable: Optional[bool] = False
    # Keep raw table data for now, specific parsing can happen if needed
    tables: Optional[List[MutationTable]] = None  # Renamed from tableData for clarity


class Attributes(BaseModel):
    # Using aliases to match JSON and allow snake_case in Python
    mental_strength: int = Field(..., ge=3, le=18, alias="mentalStrength")
    intelligence: int = Field(..., ge=3, le=18)
    dexterity: int = Field(..., ge=3, le=18)
    charisma: int = Field(..., ge=3, le=18)
    constitution: int = Field(..., ge=3, le=18)
    physical_strength: int = Field(..., ge=3, le=18, alias="physicalStrength")

    model_config = ConfigDict(
        populate_by_name=True,  # Allow creating from dicts with original keys
        alias_generator=lambda x: x,  # Keep snake_case for internal use
    )


class Character(BaseModel):
    name: Optional[str] = None
    character_type: CharacterType = Field(..., alias="characterType")
    base_animal_species: Optional[str] = Field(None, alias="baseAnimalSpecies")
    attributes: Attributes
    hit_points: int = Field(..., alias="hitPoints")
    physical_mutations: List[Mutation] = Field(default_factory=list, alias="physicalMutations")
    mental_mutations: List[Mutation] = Field(default_factory=list, alias="mentalMutations")
    generation_log: List[str] = Field(default_factory=list, alias="generationLog")
    description: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda x: x,  # Keep snake_case for internal use
    )


# --- Creature Models ---


class CreatureStats(BaseModel):
    armor_class: Optional[str] = Field(None, alias="armorClass")
    movement: Optional[str] = None
    hit_dice: Optional[str] = Field(None, alias="hitDice")
    number_appearing: Optional[str] = Field(None, alias="numberAppearing")

    model_config = ConfigDict(populate_by_name=True)


class CreatureAbility(BaseModel):
    name: str
    description: str


class Creature(BaseModel):
    name: str
    base_species: Optional[str] = Field(None, alias="baseSpecies")
    stats: CreatureStats
    special_abilities: List[CreatureAbility] = Field(default_factory=list, alias="specialAbilities")
    description: str

    model_config = ConfigDict(populate_by_name=True)


# --- API Request/Response Models ---


class CharacterSummary(BaseModel):
    id: str
    name: str
    type: str
    hit_points: Optional[int] = None
    saved: int
    image: Optional[str] = None


class SaveCharacterRequest(BaseModel):
    character: Character
    image_data: Optional[str] = None

    @field_validator("character")
    def _validate_character(cls, v):
        # Basic check, detailed validation is in Character model itself
        if not v.character_type or not v.attributes or v.hit_points is None:
            raise ValueError("Character data is incomplete (type, attributes, hp required).")
        return v


class MutationSlot(BaseModel):
    slot_id: str = Field(..., alias="slotId")
    mutation_type: MutationType = Field(..., alias="mutationType")
    type_index: int = Field(..., alias="typeIndex")
    is_choice_required: bool = Field(..., alias="isChoiceRequired")
    assigned_mutation: Optional[Mutation] = Field(None, alias="assignedMutation")
    is_defect_slot: bool = Field(False, alias="isDefectSlot")

    model_config = ConfigDict(populate_by_name=True)


class GenerateCharacterRequest(BaseModel):
    name: Optional[str] = None
    character_type: CharacterType = Field(..., alias="characterType")
    attribute_method: AttributeRollMethod = Field(
        AttributeRollMethod.HEROIC_4D6_DROP_LOWEST, alias="attributeMethod"
    )
    mutation_method: MutationSelectionMethod = Field(
        MutationSelectionMethod.RANDOM_ROLL, alias="mutationMethod"
    )
    base_animal_species: Optional[str] = Field(None, alias="baseAnimalSpecies")

    @field_validator("base_animal_species")
    def _check_species(cls, v, info):
        # Use model_dump to access validated data if needed, but info.data is usually fine here
        if info.data.get("character_type") == CharacterType.MUTATED_ANIMAL and not v:
            raise ValueError("base_animal_species is required for Mutated Animal")
        if info.data.get("character_type") != CharacterType.MUTATED_ANIMAL:
            return None  # Ensure it's None if not Mutated Animal
        return v

    model_config = ConfigDict(populate_by_name=True)


class IntermediateCharacterState(BaseModel):
    name: Optional[str] = None
    character_type: CharacterType = Field(..., alias="characterType")
    base_animal_species: Optional[str] = Field(None, alias="baseAnimalSpecies")
    attributes: Attributes
    hit_points: int = Field(..., alias="hitPoints")
    mutation_slots: List[MutationSlot] = Field(default_factory=list, alias="mutationSlots")
    assigned_mutation_names: List[str] = Field(default_factory=list, alias="assignedMutationNames")
    generation_log: List[str] = Field(default_factory=list, alias="generationLog")
    original_request: GenerateCharacterRequest = Field(
        ..., alias="originalRequest"
    )  # Store the original request

    model_config = ConfigDict(populate_by_name=True)


class GenerateCharacterResponse(BaseModel):
    needs_mutation_selection: bool = Field(..., alias="needsMutationSelection")
    intermediate_state: Optional[IntermediateCharacterState] = Field(
        None, alias="intermediateState"
    )
    character: Optional[Character] = None

    model_config = ConfigDict(populate_by_name=True)


class SelectableMutationsResponse(BaseModel):
    physical_mutations: List[Mutation] = Field(..., alias="physicalMutations")
    mental_mutations: List[Mutation] = Field(..., alias="mentalMutations")

    model_config = ConfigDict(populate_by_name=True)


class FinalizeMutationsRequest(BaseModel):
    intermediate_state: IntermediateCharacterState
    selected_mutations: Dict[str, str]  # Maps slot_id (camelCase from JS) to selected mutation name


class GenerateDescriptionRequest(BaseModel):
    name: Optional[str] = None
    character_type: CharacterType
    base_animal_species: Optional[str] = None
    attributes: Attributes
    physical_mutations: List[Mutation]
    mental_mutations: List[Mutation]


class GenerateDescriptionResponse(BaseModel):
    status: str  # 'success' or 'error'
    description: Optional[str] = None
    message: Optional[str] = None  # For error details


class GenerateImageRequest(BaseModel):
    description: str = Field(..., min_length=10)


class GenerateImageResponse(BaseModel):
    status: str  # 'success' or 'error'
    image_data: Optional[str] = None  # Base64 encoded image data
    mime_type: Optional[str] = None  # e.g., 'image/png'
    message: Optional[str] = None  # For error details


class SaveCharacterResponse(BaseModel):
    id: str
    json_path: str
    image_path: Optional[str] = None
