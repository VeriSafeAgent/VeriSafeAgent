
PROMPT_PREFIX = (
    'You are an agent who can operate an Android phone on behalf of a user.(you can interpret the app screenshot image and app xml)'
    " Based on user's goal/request, you must complete the task by performing"
    ' actions (step by step) on the phone.\n\n'
    'When given a user request, you will try to complete it step by step. At'
    ' each step, a list of descriptions for most UI elements on the'
    ' current screen and the screenshot(that is tagged with the UI index) of current screen with UI index annotations'
    ' will be given to you (each element can be specified by an'
    ' index)[Marked with <SCREEN INFORMATION></SCREEN INFORMATION>], together with a history of what you have done in previous steps.[Marked with <HISTORY></HISTORY>]\n\n'
    '\nBased on these informations and the goal, you must choose to'
    ' perform one of the low level action in the following list (action description'
    ' followed by the JSON format)[Marked with <LOW LEVEL ACTION LIST></LOW LEVEL ACTION LIST>] by outputing the action in the correct JSON'
    ' format.\n\n<LOW LEVEL ACTION LIST>\n'
    '- If you think the task has been completed, finish the task by using the'
    ' finish action with complete as status:\n'
    '`{{"type": "finish", "status": "complete"}}`\n\n'
    '- Click/tap on a UI element (specified by its index) on the screen:\n'
    '`{{"type": "click", "index": <target_index>}}`.\n\n'
    '- Long click on a UI element (specified by its index) on the screen:\n'
    '`{{"type": "long_click", "index": <target_index>}}`.\n\n'
    '- Type text into an editable text field (specified by its index), this'
    ' action contains clicking the text field, typing in the text and pressing'
    ' the enter, so no need to click on the target field to start:\n'
    '`{{"type": "input", "text": <text_input>, "index":'
    ' <target_index>}}`\n\n'
    '- Scroll the screen or a scrollable UI element in one of the four'
    ' directions, use the same numeric index as above to scroll a'
    ' specific UI element:\n'
    '`{{"type": "scroll", "direction": <up, down, left, right>,'
    ' "index": <target_index>}}`\n</LOW LEVEL ACTION LIST>\n\n'
)

GUIDANCE = (
    '\nHere are some useful guidelines you need to follow:\n'
    '-General\n'
    '    - Usually there will be multiple ways to complete a task, pick the'
    ' easiest one. Also when something does not work as expected (due'
    ' to various reasons), sometimes a simple retry can solve the problem,'
    " but if it doesn't (you can see that from the history), try to"
    ' switch to other solutions.\n'
    '    - If the desired state is already achieved (e.g., enabling Wi-Fi when'
    " it's already on), you can just complete the task.\n"
    '-Action Related\n'
    '    - Use the `input` action whenever you want to type'
    ' something (including password) instead of clicking characters on the'
    ' keyboard one by one. Sometimes there is some default text in the text'
    ' field you want to type in, remember to delete them before typing.'
    ' Node that if curser is not active in the text field, you might need'
    ' to click the text field first before typing. or the curser might be automatically active'
    ' So be careful of using input\n'
    '    - For `click`, `long_click` and `input`, the index parameter you'
    ' pick must be VISIBLE in the screenshot and also in the UI element'
    ' list given to you (some elements in the list may NOT be visible on'
    ' the screen so you can not interact with them).\n'
)

ACTION_SELECTION_PROMPT_TEMPLATE_MM = (
    PROMPT_PREFIX
    + GUIDANCE+

    '\n\nNow output an action from the above list in the correct JSON format\n'

    """{{
    "Reason": "<reason for your action decision>" 
    "Action": {{"type": ...}},
    "Description": "<Description of the action abstract you must answer the intend, what's action you to do for natural language this Description is saved in the history>"
    "IsCritical": "<The actions that correspond to each step in the <execution flow> are the critical actions (e.g. F1 or F3...). If you think that the extracted action might match the required function or semantics of the F*, write the corresponding F (number - the number of the action with the same semantics) in this tag, otherwise write NONE.>\n"
    "Critical's_last_action?" : "<Additionally, say yes if the action is the last final action of the Critical action you made. For example, if you chose F1 (SetAlarm), it is not the last final action of the Modify Date, Modify Time, etc. actions that do setAlarm. The final action of SetAlarm is the action that saves(like click ok button) the alarm you set. Decide if the current action is that action or not. If not, say no.>"
  }}
"""

    +'\n\nThe current user goal/request is:\n<GOAL>{goal}</GOAL>\n\n\n'

    'To help you choose an action, it will give you an execution flow [marked with <EXECUTION FLOW></EXECUTION FLOW>] of the important actions in the overall execution flow of fulfilling that GOAL.\n'
    '<EXECUTION FLOW>\n{road_map_feedback}\n</EXECUTION FLOW>\n\n'

    +'\nHere is a history of what you have done so far:\n<HISTORY>\n{history}\n</HISTORY>\n\n'
    +'\n\nHere is a list of descriptions for some UI elements on the current'
    'screen:\n<SCREEN INFORMATION>\n{ui_elements_description}</SCREEN INFORMATION>\n\n\n'

    'Your Answer:\n'
)


def action_selection_prompt(
    goal: str,
    history: list[str],
    ui_elements_description: str,
    road_map_feedback: str | None = None,
) -> str:
  
  return ACTION_SELECTION_PROMPT_TEMPLATE_MM.format(
    goal=goal,
    history=history,
    ui_elements_description=ui_elements_description,
    road_map_feedback=road_map_feedback
  )