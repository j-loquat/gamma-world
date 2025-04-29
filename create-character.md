**Gamma World Character Creation Process**

The process involves selecting a character type, determining basic abilities through dice rolls, potentially adding mutations, and calculating derived stats like Hit Points.

**Phase 1: Choose Character Type**

The player must first decide which fundamental type of character they wish to portray. This choice significantly impacts abilities and interactions within the game world.

1.  **Player Selects One Type:**
    *   **Pure Strain Human (PSH):**
        *   **Description:** Descendants of pre-holocaust humans with *no* mutations.
        *   **Special Rules:**
            *   Automatically gain a +3 bonus to their rolled Charisma score (cannot exceed 18).
            *   Often recognized by pre-2322 robotic units and security systems.
            *   May have some familiarity with Ancient technology/ruins.
            *   Vulnerable due to lack of mutations but respected/feared by some mutants.
        *   **Mutation Step:** PSH characters *skip* the Mutation determination phase entirely.
    *   **Humanoid:**
        *   **Description:** Descendants of human stock who *have* undergone mutation. This is considered the "standard" survivor type.
        *   **Special Rules:**
            *   Undergo the full Mutation determination process (Phase 3).
            *   May pass *some* security checks if mutations are not physically obvious and they possess proper ID (Referee discretion).
    *   **Mutated Animal:**
        *   **Description:** An animal species that has mutated, gaining intelligence and other abilities.
        *   **Initial Player Choice:** Player selects a base animal species (e.g., bear, cat, wolf, eagle).
        *   **Referee Adjudication:** Before proceeding, the Referee must determine:
            *   Can the animal speak?
            *   Can its paws/hooves/fins/etc., function as hands for manipulating objects? (This requires logical interpretation based on the species).
        *   **Special Rules:**
            *   Automatically gain human-equivalent intelligence *before* rolling attributes. This base intelligence does *not* count as a mutation (like "Heightened Intelligence").
            *   Undergo the full Mutation determination process (Phase 3).
            *   *Cannot* normally command robotic units or pass security checks designed for humans.

**Phase 2: Determine Basic Attributes**

Every character has six fundamental attributes representing their innate capabilities.

1.  **Identify the Six Attributes:**
    *   Mental Strength (MS)
    *   Intelligence (IN)
    *   Dexterity (DX)
    *   Charisma (CH)
    *   Constitution (CN)
    *   Physical Strength (PS)

2.  **Choose Rolling Method (Referee decides or offers choice):**
    *   **Method 1 (Standard):** Roll 3d6 for each attribute, in order. Sum the dice for the score (range 3-18).
        *   *General Guide:* 3-8 is weak, 9-12 is average, 13-18 is above average.
    *   **Method 2 (Recommended/Heroic):** Roll 4d6 for each attribute. Discard the lowest die roll. Sum the remaining three dice for the score (range 3-18, but weighted towards higher scores).

3.  **Record Attribute Scores:** Note the score for each of the six attributes.

4.  **Apply PSH Charisma Bonus (If Applicable):** If the character is a Pure Strain Human, add +3 to the rolled Charisma score (maximum score remains 18).

5.  **Note Attribute Implications (Summary - details applied during play or later steps):**
    *   **MS:** Governs mental attack/defense (if mutated) or just mental defense (if PSH). *Can increase with use during play.*
    *   **IN:** Affects artifact analysis rolls (bonus/penalty points above 15/below 7). Guides logical actions.
    *   **DX:** Influences initiative, first strike, and physical "to hit" rolls (bonus/penalty points above 15/below 6). Represents agility and reaction time.
    *   **CH:** Affects reactions of NPCs (see Reaction Table, p.8), maximum number of loyal followers, and follower morale (see Charisma Table, p.8). Consider inter-type modifiers (p.9).
    *   **CN:** Determines starting Hit Points (see Phase 4). Affects saving throws vs. Poison and Radiation (see Hazards, p.28-29). *Generally does not change.*
    *   **PS:** Affects damage dealt in physical combat (bonus/penalty points above 15/below 6). Represents raw muscle power.

**Phase 3: Determine Mutations (Humanoids & Mutated Animals Only)**

This phase grants the special abilities (and sometimes drawbacks) that define mutated characters. PSH characters skip this phase.

1.  **Determine *Number* of Mutations:**
    *   Roll 1d4 once. This is the number of **Physical Mutations** the character has. Record the result. The complete table and descriptions for Physical Mutations is in the file "Physical-Mutations.json".
    *   Roll 1d4 again. This is the number of **Mental Mutations** the character has. Record the result. The complete table and descriptions for Mental Mutations is in the file "Mental-Mutations.json".
    *   *Crucial:* Keep track of the actual numbers rolled (e.g., a '3' or '4') as this influences defect assignment in Method 2 below.

2.  **Determine *Specific* Mutations (Choose one method - Referee decides or offers choice):**
    *   **Method 1 (Random Roll):**
        *   For each Physical mutation indicated by the 1d4 roll, the player rolls percentile dice (d100 or 2d10) and consults the Physical Mutations table (p.10).
        *   For each Mental mutation indicated by the 1d4 roll, the player rolls percentile dice (d100 or 2d10) and consults the Mental Mutations table (p.12).
        *   Record the resulting mutations.
        *   *Defects:* If a rolled mutation has a "(D)" next to it on the chart, it is a defect. The character gains this defect as rolled. (Note: Rolls of 91-94 allow rerolling a non-defect mutation, 95-100 allow picking any mutation).
    *   **Method 2 (Player Choice + Referee Defect Assignment):**
        *   The player *chooses* the specific Physical and Mental mutations they desire, up to the number determined by the 1d4 rolls in Step 1. (They select from the lists on pages 10-14, avoiding entries marked with "(D)" unless they *want* a defect as a choice).
        *   *Referee Assigns Defects:* After the player chooses their mutations, the Referee reviews the *original 1d4 rolls* for the *number* of mutations and assigns defects as follows:
            *   If the d4 roll for the *number* of Physical mutations was a 3 or 4: Assign one Physical Defect.
            *   If the d4 roll for the *number* of Mental mutations was a 3 or 4: Assign one Mental Defect.
            *   If *both* d4 rolls were 3 or 4: Assign one Physical *and* one Mental Defect.
            *   If *both* d4 rolls were 2: Assign *either* one Physical *or* one Mental Defect (Referee's choice).
            *   If the *sum* of the two d4 rolls was 3 or less: Assign *no* defects via this method.
            *   The Referee selects appropriate defects from the mutation lists (marked with "(D)").

3.  **Record Mutations and Defects:** List all acquired mutations and defects on the character sheet.

**Phase 4: Calculate Derived Statistics**

Based on the attributes, calculate secondary characteristics.

1.  **Calculate Hit Points (HP):**
    *   The character's starting Hit Points are determined by their Constitution (CN) score.
    *   Roll a number of six-sided dice (d6) equal to the character's CN score.
    *   Sum the results of all the dice rolled. This total is the character's starting HP.
    *   Record the HP.

**Phase 5: Final Review**

A final check before play begins.

1.  **Hopeless Character Check (Referee Discretion):**
    *   Review the character's attributes. If most or all attributes are significantly below average (generally in the 3-8 range), the Referee has the *option* to declare the character "Hopeless."
    *   If declared Hopeless, the player is allowed to discard the character and start the creation process over. This is entirely at the Referee's discretion to ensure playability.

This breakdown covers the core character generation rules as presented.