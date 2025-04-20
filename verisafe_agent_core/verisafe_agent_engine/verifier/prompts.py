feedback_prompt = """Here is the your past chc encodings and equivalence check results.

<Feedback>
{feedback_list}
</Feedback>

Now, you need to encode the following instruction referring to the past feedbacks.
Never encode the instruction as same as the past.
Also, you need to understand why the past encodings are wrong and how to improve them in the <Think> section.
"""

normal_prompt = """**User Input**
{instruction}
{driven_experience}
{predicates}

**Response**
"""

nl_based_equiv_checker_system_prompt = """Your task is to check whether the target instruction is correct compared to the oracle instruction.
Note that these are instructions that will be passed to future app agents.
What we mean by **correct** is that the target instruction is correct compared to the oracle instruction.
Before you check, you must fully understand the user inputs in <Think> section step by step.
After <Think> section, you need to check whether the target instruction is correct compared to the oracle instruction.
In <Result> section, you need to give your final result in True or False.

**Guidelines**
1. Don't compare the two instruction literally. If they use different words but the same meaning, you should consider them equivalent.
2. think about what app you're using and understand the instructions accordingly. Understand the context in a way that is specific to that app.
3. Use the following procedure to verify that the target instruction is the same as the oracle instruction.
  1. Check all the conditions of the target instruction and the oracle instruction in turn.
  2. Verify that the conditions of the target instruction are the same as the conditions of the oracle instruction.
  3. If the conditions in the target instruction are different from the conditions in the oracle instruction, see where they differ.
  4. If the differences from the oracle conditions are generally negligible, judge the target instruction as correct.
  5. If the target instruction is missing something and it is not negligible, judge the target instruction as invalid.

# Example Format
<OracleInstruction>
...
</OracleInstruction>
<TargetInstruction>
...
</TargetInstruction>

<Think>
...
</Think>
<Result>
True or False
</Result>

---

Now you turn."""

nl_based_equiv_checker_user_prompt = """<OracleInstruction>
{oracle_instruction}
</OracleInstruction>
<TargetInstruction>
{target_instruction}
</TargetInstruction>"""

chc_based_equiv_checker_system_prompt = """Your task is to check whether the target chc formulas is correct compared to the oracle natural language instruction.
Note that these are chc formulas that will be passed to future app agents.
What we mean by **correct** is that the target chc formulas is correct compared to the oracle natural language instruction.
Before you check, you must fully understand the user inputs in <Think> section step by step.
After <Think> section, you need to check whether the target chc formulas is correct compared to the oracle natural language instruction.
You can refer the description of the predicates in <Predicates> section.
In <Result> section, you need to give your final result in True or False.

**Guidelines**
1. Don't compare the two instruction literally. If they use different words but the same meaning, you should consider them equivalent.
2. think about what app you're using and understand the instructions accordingly. Understand the context in a way that is specific to that app.
3. Use the following procedure to verify that the target chc formulas is the same as the oracle natural language instruction.
  1. Check all the conditions of the target chc formulas and the oracle natural language instruction in turn.
  2. Verify that the conditions of the target chc formulas are the same as the conditions of the oracle natural language instruction.
  3. If the conditions in the target chc formulas are different from the conditions in the oracle natural language instruction, see where they differ.
  4. If the differences from the oracle conditions are generally negligible, judge the target chc formulas as correct.
  5. If the target chc formulas is missing something and it is not negligible, judge the target chc formulas as invalid.

# Example Format
<Predicates>
...
</Predicates>
<OracleInstruction>
...
</OracleInstruction>
<TargetCHC>
...
</TargetCHC>

<Think>
...
</Think>
<Result>
True or False
</Result>

---

Now your turn.
"""

chc_based_equiv_checker_user_prompt = """<Predicates>
{predicates}
</Predicates>
<OracleInstruction>
{oracle_instruction}
</OracleInstruction>
<TargetCHC>
{target_chc}
</TargetCHC>"""

logical_structure_constraints = f"""**Logical Structure**:
  - Encode each condition as a **constrained implication** using Horn clause notation:
    - `Condition1 ∧ Condition2 ∧ ... ∧ ConditionN → Action`.
  - Generate Conditions using only provided predicates. List of predicates will be provided as an input. Each predicate has a name, description, and arguments. Predicates are represent state of the application. Action can be created by yourself.
    - Predicate structure:
      - `PredicateName(arg_name: arg_type, arg_name: arg_type, ...): <description>`
      - Example: `GrocerySearchOptions(item_name: Text, item_count: Number, price_upper_bound: Number): Represents the options for grocery search.`
    - Action structure:
      - You cannot use any argument for action. Action has only name.
      - `ActionName()`
  - Fill in the predicate arguments with the following constraints:
    - Type of predicate arguments:
      - Boolean: `arg_name: Boolean`. Value format=True or False. For example, `is_available=True`
      - Text: `arg_name: Text`. Value format=any string value. For example, `service_name=Uber`
      - Number: `arg_name: Number`. Value format=(any integer value, comparison operators). For example, `price=(10000, >)`
      - Date: `arg_name: Date`. Value format=(YYYY-MM-DD, comparison operators). For example, `StartDate=(2025-01-01, ==)`, `EndDate=(2025-01-01, !=)`
      - Time: `arg_name: Time`. Value format=(HH:MM:SS, comparison operators). For example, `StartTime=(12:00:00, ==)`, `EndTime=(12:00:00, !=)`
      - Enum: `arg_name: Enum[enum_value1, enum_value2, ...]`. Value format=(enum values). For example, `tab_description=Feed`
    - Omit the value if any value can be used.
    - Kind of comparison operators:
      - `==`: Equal (e.g., `price=(10000, ==)`)
      - `!=`: Not equal (e.g., `price=(10000, !=)`)
      - `>`: Greater than (e.g., `price=(10000, >)`)
      - `<`: Less than (e.g., `price=(10000, <)`)
      - `>=`: Greater than or equal (e.g., `price=(10000, >=)`)
      - `<=`: Less than or equal (e.g., `price=(10000, <=)`)
      - If you omit the comparison operator, it is considered as `==`. For example, `price=(10000)` is the same as `price=(10000, ==)`.
    - You do not need to use all the arguments of the predicate. You can use as many or as few as you need.
    - You must precisely read the description of each predicate to understand its meaning and use it correctly.
  - Guideline for branching:
    - If the instruction includes some branching logic, you have to express the branching logic by using CHCs.
    - You cannot use any negation or disjunction in the condition. If you want to negate, then flip the comparison operator. For example, negation of `price=(10000, ==)` is `price=(10000, !=)`.
      - Reference:
        - True <-> False
        - `==` <-> `!=`
        - `>` <-> `<=`
        - `<` <-> `>=`
    - If there is some conditional action like `if some condition, then do action`, you must add false branch to the CHC even though it is not written in the instruction.
    - Branch Example:
      - Instruction: If C1 and C2, do Action1. If C3 and C4, do Action2. After Action1, and C5(arg=True) is satisfied, do Action3.
      - CHC:
        - C1() ∧ C2() → Action1()
        - C3() ∧ C4() → Action2()
        - Action1() ∧ C5(arg=True) → Action3()
        - Action1() ∧ C5(arg=False) → Done()
  - Guidelines for repeating action:
    - You can use one action name only once as an action (right side of the →).
    - If the instruction requires to do the same action multiple times, you must add RepeatN as a postfix of the action name. For example, `ClickLikeRepeat3()`. Then parser automatically unroll the action like:
      - C1() ∧ C2() → ClickLikeRepeat3() into
        - C1() ∧ C2() → ClickLike1()
        - ClickLike1() ∧ C1() ∧ C2() → ClickLike2()
        - ClickLike2() ∧ C1() ∧ C2() → ClickLike3()
      - You don't need to unroll yourself. Just add RepeatN as a postfix of the action name.
    - If the instruction requires do some action for all the things which satisfies the condition, you must add `All` as a postfix of the action name. For example, `OrderAll()`
  - Guidelines for order of instrucion:
    - If there is some dependency between the actions, you must add the dependency to the CHC. For example, if Action1 must be done before Action2, you must add the dependency like:
      - C1() ∧ C2() → Action1()
      - Action1() ∧ C3() → Action2()
  - Action must be specified in the natural language instruction as verb. You cannot add any action that you arbitrarily decided. You must use only the action that is expressed as a verb in the instruction."""


instruction_decoding_prompt = f"""You are an AI system designed to transform **Constrained Horn Clauses (CHC)** into **mobile app instructions**.
1. User input is a list of CHC which represents the instruction for the mobile agent.
2. Your task is to transform the CHC into the mobile app instruction in natural language.
3. You must include all the details of the CHC in the instruction. It means that every predicates can be restored from the instruction.
4. Instruction can be multiple sentences.
5. You can find the definition and description of the predicates in the <Predicates> section.

Here is background knowledge about **Constrained Horn Clauses (CHC)**:
{logical_structure_constraints}

Here is some examples of how to decode the CHC into the mobile app instruction from the user input.

# Example

** User Input **
<Predicates>
- OrderInformation(address: String, receiver: String, phone_number: String, total_price: Number): Information about the order. `address` is the address of the order. `receiver` is the name of the recipient. `phone_number` is the phone number of the recipient. `total_price` is the total price of the order.
- Merchandise(name: String, price_per_unit: Number, quantity: Number): Information about the merchandise in my cart. `name` is the name of the merchandise. `price_per_unit` is the price per unit of the merchandise. `quantity` is the quantity of the merchandise.
</Predicates>
<CHC>
    1. OrderInformation(address="home", receiver="me") ∧ Merchandise(name="pepperoni pizza", quantity=2) ∧ Merchandise(name="cheese pizza", quantity=1) → Order()
</CHC>

** Output **
<Instruction>
Order me two pepperoni pizzas and one cheese pizza.
</Instruction>

---

Now you turn.
"""


instruction_encoding_system_prompt = f"""# Instruction

You are an AI system designed to transform mobile app instructions into single **Constrained Horn Clauses (CHC)**. Your outputs must meet the following criteria:

1. **Detailed Condition Specification**:
   - Translate each instruction into **atomic predicates** representing conditions, states, and actions.
   - Ensure that predicates include sufficient detail to enable verification through observations of the agent's actions and the system's state.
   - Don't guess the intermediate states too much. Just encode the stated conditions.

2. {logical_structure_constraints}

3. **Extra Constraints**:
  - If there is no condition for do the action, you can use `True` as the condition. For example, `True → ClickFirstContent()`
  - Before you start, you need to think about the instruction step by step in the <Think> section. In the think section, you need to consider the following:
    - What is the user's goal?
    - What is the user's action?
    - What is the user's condition?
    - Which predicate is the most relevant to the user's goal?
    - Which arguments of the predicate are necessary?
  - You cannot use predicates defined in the <Predicates> section in the action.
  - If there is some option about the sorting or filtering, you need to consider the option in the predicate.
  - You must not add conditions arbitrarily.


# Examples
Here is some examples of how to encode the instruction into CHC from the user input.
Natural Language Instruction and List of Predicates are provided as an user input.

## Normal Example1

**User Input**:
<Predicates>
- OrderInformation(address: String, receiver: String, phone_number: String, total_price: Number): Information about the order. `address` is the address of the order. `receiver` is the name of the recipient. `phone_number` is the phone number of the recipient. `total_price` is the total price of the order.
- Merchandise(name: String, price_per_unit: Number, quantity: Number): Information about the merchandise in my cart. `name` is the name of the merchandise. `price_per_unit` is the price per unit of the merchandise. `quantity` is the quantity of the merchandise.
</Predicates>
<Instruction>
Open the Delivery app and order me two pepperoni pizzas and one cheese pizza.
</Instruction>


**Response:**
<Think>
...
</Think>
<CHC>
1. OrderInformation(address="home", receiver="me") ∧ Merchandise(name="pepperoni pizza", quantity=2) ∧ Merchandise(name="cheese pizza", quantity=1) → Order()
</CHC>

---

## Normal Example2

**User Input**:
<Predicates>
- Post(author: String, content: String, created_at_date: Date, created_at_time: Time, liked: Boolean): Represents a post information which currently displayed on the screen. `author` is the author of the post. `content` is the content of the post. `created_at_date` is the date when the post was created. `created_at_time` is the time when the post was created. `liked` is the flag that the you liked the post.
- CurrentTab(tab_description: Enum["Feed", "Search", "Notification", "Profile"]): Represents the current tab of the Instagram.
- Setting(option_name: Enum["Notification", "Theme", "Language", "Privacy", "Security", "Payment"], enabled: Boolean): Represents the setting of the Instagram. `option_name` is the name of the option. `enabled` is the flag that the option is enabled.
- DirectMessage(sender: String, content: String, created_at_date: Date, created_at_time: Time): Represents a direct message on the Instagram. `sender` is the sender of the message. `content` is the content of the message. `created_at_date` is the date when the message was created. `created_at_time` is the time when the message was created.
- FeedSortBy(sort_by: Enum["Latest", "Oldest", "Most Liked"]): Represents the sort by of the feed. `sort_by` is the sort by of the feed.
</Predicates>
<Instruction>
Find out the lastest post and click the like from the feed of SNS App.
</Instruction>


**Response**:
<Think>
...
</Think>
<CHC>
1. CurrentTab(tab_description="Feed") ∧ FeedSortBy(sort_by="Latest") → ClickLike()
</CHC>
---
## Branching Example1
**User Input**:
<Predicates>
- CurrentQuery(query: String): Represents the current query of the Map Application search bar.
- Restaurant(name: String, description: String, review_count: Number, rating: Number): Represents a restaurant information currently displayed on the screen. `name` is the name of the restaurant. `description` is the description of the restaurant. `review_count` is the number of reviews of the restaurant. `rating` is the rating of the restaurant.
- LikedRestaurant(name: String, description: String): Represents a restaurant information which I liked. `name` is the name of the restaurant. `description` is the description of the restaurant.
- QuerySortBy(sort_by: Enum["Relevance", "Distance", "Rating"]): Represents the sort by of the query. `sort_by` is the sort by of the query.
</Predicates>
<Instruction>
Search "korean food" on Map Application and click the first result. If the number of review is more than 100 and the rating is more than 4.5, do reservation.
</Instruction>


**Response**:
<Think>
...
</Think>
<CHC>
1. CurrentQuery(query="korean food") ∧ Restaurant(review_count=(100, >), rating=(4.5, >)) → Reservation()
2. CurrentQuery(query="korean food") ∧ Restaurant(review_count(100, <=)) → Done()
3. CurrentQuery(query="korean food") ∧ Restaurant(rating(4.5, <=)) → Done() # You must add false branch even though it is not written in the instruction.
</CHC>
---
## Branching Example2
**User Input**:
<Predicates>
- Post(author: String, content: String, created_at_date: Date, created_at_time: Time, liked: Boolean, number_of_likes: Number): Represents a post information which currently displayed on the screen. `author` is the author of the post. `content` is the content of the post. `created_at_date` is the date when the post was created. `created_at_time` is the time when the post was created. `liked` is the flag that the you liked the post. `number_of_likes` is the number of likes of the post.
- PostSortBy(sort_by: Enum["Latest", "Oldest", "Most Liked"]): Represents the sort by of the post. `sort_by` is the sort by of the post.
- CurrentWritingComment(content: String): Represents the content of the comment that you are writing. `content` is the content of the comment that you are writing.
- CurrentWritingPost(content: String): Represents the content of the post that you are writing. `content` is the content of the post that you are writing.
- Following(name: String): Represents the name of the following user. `name` is the name of the following user.
- Follower(name: String): Represents the name of the follower user. `name` is the name of the follower user.
- Setting(option_name: Enum["Notification", "Theme", "Language", "Privacy", "Security", "Payment"], enabled: Boolean): Represents the setting of the Instagram. `option_name` is the name of the option. `enabled` is the flag that the option is enabled.
</Predicates>
<Instruction>
Find out the post which has the most likes. If you already liked the post, write comment. If not, click the like button and write the comment. Comment content is "Hello!".
</Instruction>


**Response**:
<Think>
...
</Think>
<CHC>
1. PostSortBy(sort_by="Most Liked") ∧ Post(liked=False) → ClickLike()
2. PostSortBy(sort_by="Most Liked") ∧ Post(liked=True) → WriteComment()
3. WriteComment() ∧ CurrentWritingComment(content="Hello!") → UploadComment()
4. ClickLike() ∧ CurrentWritingPost(content="Hello!") → UploadPost()
</CHC>
---
## Repeating Example
<Predicates>
- Post(author: String, content: String, created_at_date: Date, created_at_time: Time, liked: Boolean, number_of_likes: Number): Represents a post information which currently displayed on the screen. `author` is the author of the post. `content` is the content of the post. `created_at_date` is the date when the post was created. `created_at_time` is the time when the post was created. `liked` is the flag that the you liked the post. `number_of_likes` is the number of likes of the post.
- Tab(tab_description: Enum["Home", "Post", "Search", "Notification", "Profile"]): Represents the current tab of the app. `tab_description` is the description of the current tab.
- PostSortBy(sort_by: Enum["Latest", "Oldest", "Most Liked"]): Represents the sort by of the post. `sort_by` is the sort by of the post.
</Predicates>
<Instruction>
Sort the post by "Latest" and click the like for first 3 posts.
</Instruction>


**Response**:
<Think>
...
</Think>
<CHC>
1. Tab(tab_description="Post") ∧ PostSortBy(sort_by="Latest") → ClickLikeRepeat3()
</CHC>



---
## Dependency Example
**User Input**:
<Predicates>
- TaskList(name: String, task_name: String, number_of_tasks: Number): Represents a task list. `name` is the name of the task list. `task_name` is the name of the task. `number_of_tasks` is the number of tasks in the task list.
- Task(name: String, description: String): Represents a task. `name` is the name of the task. `description` is the description of the task.
- Tab(tab_description: Enum["Home", "Task", "Calendar"]): Represents the current tab of the app. `tab_description` is the description of the current tab.
- TaskListSortBy(sort_by: Enum["Latest", "Oldest", "Most Liked"]): Represents the sort by of the task list. `sort_by` is the sort by of the task list.
</Predicates>
<Instruction>
Generate your own task list named "Study". After that, add 3 tasks named "Read Book", "Solve Math Problem", and "Solve Coding Problem".
</Instruction>


**Response**:
<Think>
...
</Think>
<CHC>
1. True → CreateTaskList()
2. CreateTaskList() ∧ TaskList(name="Study") → CreateTaskDone()
3. CreateTaskDone() ∧ Task(name="Read Book") → AddTaskReadBook()
4. CreateTaskDone() ∧ Task(name="Solve Math Problem") → AddTaskSolveMathProblem()
5. CreateTaskDone() ∧ Task(name="Solve Coding Problem") → AddTaskSolveCodingProblem()
6. TaskList(name="Study", number_of_tasks=3) → Done()
</CHC>
---
Now, your turn"""

instruction_encoding_user_prompt_predicates = """<Predicates>
{predicates}
</Predicates>
"""

instruction_encoding_user_prompt_memory_begin = """It contains past instructions that were similar to the current instructions. Use this information to encode the current instruction.
There are four main types of information: `PastInstruction`, `PastExecutionFlow`, `PastRelevantPredicates`, and `PastCHCs`.
`PastInstruction` is a past instruction.
`PastExecutionFlow` is the flow of the past instruction on the target app.
`PastRelevantPredicates` are the conditions used in past instructions. You should consider to use these predicates in the current instruction encoding first.
`PastCHCs` is the CHCs generated from past instructions.

Each is separated by the tags <PastInstruction>, <PastExecutionFlow>, <PastRelevantPredicates>, and <PastCHCs>.
"""

instruction_encoding_user_prompt_memory_fewshot_template = """
# Example {idx}
<PastInstruction>
{past_instruction}
</PastInstruction>
<PastExecutionFlow>
{past_execution_flow}
</PastExecutionFlow>
<PastRelevantPredicates>
{past_relevant_predicates}
</PastRelevantPredicates>
<PastCHCs>
{past_chcs}
</PastCHCs>
"""

instruction_prompt = """Now, you please encode the following instruction.
<Instruction>
{instruction}
</Instruction>
"""
