from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Input, Static

if TYPE_CHECKING:
    from vibe.core.tools.builtins.ask_user import AskUserArgs, Question


class EscapableInput(Input):
    """Input that posts escape events to parent."""

    class EscapePressed(Message):
        """Escape was pressed in the input."""

        pass

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self.post_message(self.EscapePressed())


class QuestionTab(Static):
    """A single tab in the tab bar."""

    def __init__(self, label: str, index: int, is_active: bool = False) -> None:
        super().__init__(classes="question-tab")
        self.tab_label = label
        self.tab_index = index
        self.is_active = is_active

    def on_mount(self) -> None:
        self._update_display()

    def set_active(self, active: bool) -> None:
        self.is_active = active
        self._update_display()

    def _update_display(self) -> None:
        self.update(self.tab_label)
        if self.is_active:
            self.add_class("question-tab-active")
        else:
            self.remove_class("question-tab-active")


class QuestionPanel(Container):
    """Panel showing a single question's choices."""

    can_focus = True
    can_focus_children = True

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    class CancelRequested(Message):
        """Bubble up cancel request to parent."""

        pass

    def action_cancel(self) -> None:
        self.post_message(self.CancelRequested())

    def on_escapable_input_escape_pressed(
        self, message: EscapableInput.EscapePressed
    ) -> None:
        """Handle escape from input."""
        self.post_message(self.CancelRequested())

    def on_key(self, event: events.Key) -> None:
        """Handle escape when panel is focused."""
        if event.key == "escape":
            event.stop()
            self.post_message(self.CancelRequested())

    def __init__(self, question: Question, index: int, max_choices: int = 6) -> None:
        super().__init__(classes="question-panel")
        self.question_data = question
        self.index = index
        self.choices = question.choices or []
        self.max_choices = max_choices

        # Selection state
        self.selected_option = 0
        self.total_options = len(self.choices) + 1  # +1 for "Other"
        self.option_widgets: list[Static] = []

        # Text input for "Other" option
        self.text_input: Input | None = None
        self.other_cursor: Static | None = None
        self.is_other_mode = False

    def compose(self) -> ComposeResult:
        # Question text (will be highlighted when active)
        yield Static(self.question_data.question, classes="question-text")

        # Choice options
        for _ in range(len(self.choices)):
            widget = Static("", classes="question-option")
            self.option_widgets.append(widget)
            yield widget

        # "Other" option as inline input with cursor prefix
        with Horizontal(classes="question-other-line"):
            self.other_cursor = Static("  ", classes="question-other-cursor")
            yield self.other_cursor
            self.text_input = EscapableInput(
                placeholder="_",
                classes="question-other-input",
            )
            yield self.text_input

        # Dynamic padding: fill remaining space based on max choices
        padding_lines = self.max_choices - len(self.choices)
        if padding_lines > 0:
            yield Static("\n" * (padding_lines - 1), classes="question-padding")

    async def on_mount(self) -> None:
        self._update_options()

    def _update_options(self) -> None:
        for idx, widget in enumerate(self.option_widgets):
            is_selected = idx == self.selected_option

            choice = self.choices[idx]
            text = choice.label
            if choice.description:
                text += f" - {choice.description}"

            cursor = "> " if is_selected else "  "
            widget.update(f"{cursor}{text}")

            widget.remove_class("question-option-selected")
            if is_selected:
                widget.add_class("question-option-selected")

        # Update "Other" cursor
        is_other_selected = self.selected_option == len(self.choices)
        was_other_mode = self.is_other_mode

        if self.other_cursor:
            self.other_cursor.update("> " if is_other_selected else "  ")

        if self.text_input:
            self.is_other_mode = is_other_selected
            if is_other_selected:
                self.text_input.focus()
            elif was_other_mode:
                self.focus()

    def move_up(self) -> None:
        self.selected_option = (self.selected_option - 1) % self.total_options
        self._update_options()

    def move_down(self) -> None:
        self.selected_option = (self.selected_option + 1) % self.total_options
        self._update_options()

    def get_answer(self) -> tuple[str, bool]:
        """Get the current answer and whether it's an 'Other' response."""
        if self.selected_option < len(self.choices):
            return self.choices[self.selected_option].label, False
        else:
            if self.text_input:
                return self.text_input.value.strip(), True
            return "", True

    def focus_input(self) -> None:
        """Focus the appropriate input for this question."""
        if self.is_other_mode and self.text_input:
            self.text_input.focus()
        else:
            self.focus()


class QuestionApp(Container):
    """Widget for asking the user one or more questions with tabs."""

    can_focus = True
    can_focus_children = True

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("left", "prev_tab", "Previous Tab", show=False),
        Binding("right", "next_tab", "Next Tab", show=False),
        Binding("tab", "next_tab", "Next Tab", show=False),
        Binding("shift+tab", "prev_tab", "Previous Tab", show=False),
        Binding("enter", "submit", "Submit", show=False),
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    class Answered(Message):
        """Message sent when user answers all questions."""

        def __init__(self, answers: list[tuple[str, str, bool]]) -> None:
            super().__init__()
            # List of (question, answer, is_other)
            self.answers = answers

    class Cancelled(Message):
        """Message sent when user cancels."""

        pass

    def __init__(self, args: AskUserArgs) -> None:
        super().__init__(id="question-app")
        self.args = args
        self.questions = args.questions
        self.current_tab = 0
        self.tab_widgets: list[QuestionTab] = []
        self.panel_widgets: list[QuestionPanel] = []
        # Calculate max choices across all questions for consistent padding
        self.max_choices = max(len(q.choices) for q in self.questions) if self.questions else 6

    def compose(self) -> ComposeResult:
        with Vertical(id="question-content"):
            # Tab bar (only if multiple questions)
            if len(self.questions) > 1:
                with Horizontal(classes="question-tabs"):
                    for i, q in enumerate(self.questions):
                        label = f"Q{i + 1}"
                        tab = QuestionTab(label, i, is_active=(i == 0))
                        self.tab_widgets.append(tab)
                        yield tab

            # Question panels (only one visible at a time)
            with Container(classes="question-panels-container"):
                for i, q in enumerate(self.questions):
                    panel = QuestionPanel(q, i, max_choices=self.max_choices)
                    panel.display = (i == 0)  # Only first visible
                    self.panel_widgets.append(panel)
                    yield panel

            # Help text
            yield Static(self._get_help_text(), classes="question-help")

    def _get_help_text(self) -> str:
        if len(self.questions) > 1:
            return "←→/Tab: switch question  |  ↑↓: select  |  Enter: submit all  |  Escape: cancel"
        else:
            return "↑↓: select  |  Enter: submit  |  Escape: cancel"

    async def on_mount(self) -> None:
        # Focus the first panel and highlight its question
        if self.panel_widgets:
            self.panel_widgets[0].query_one(".question-text").add_class("question-text-active")
            self.call_after_refresh(self.panel_widgets[0].focus_input)

    def _get_current_panel(self) -> QuestionPanel | None:
        if 0 <= self.current_tab < len(self.panel_widgets):
            return self.panel_widgets[self.current_tab]
        return None

    def _switch_tab(self, new_tab: int) -> None:
        if new_tab == self.current_tab:
            return

        # Update tab appearance
        if self.tab_widgets:
            self.tab_widgets[self.current_tab].set_active(False)
            self.tab_widgets[new_tab].set_active(True)

        # Update question text highlight
        old_panel = self.panel_widgets[self.current_tab]
        new_panel = self.panel_widgets[new_tab]
        old_panel.query_one(".question-text").remove_class("question-text-active")
        new_panel.query_one(".question-text").add_class("question-text-active")

        # Hide old panel, show new panel
        old_panel.display = False
        new_panel.display = True

        self.current_tab = new_tab

        # Focus the new panel
        new_panel.focus_input()

    def action_move_up(self) -> None:
        panel = self._get_current_panel()
        if panel:
            panel.move_up()

    def action_move_down(self) -> None:
        panel = self._get_current_panel()
        if panel:
            panel.move_down()

    def action_next_tab(self) -> None:
        if len(self.panel_widgets) > 1:
            new_tab = (self.current_tab + 1) % len(self.panel_widgets)
            self._switch_tab(new_tab)

    def action_prev_tab(self) -> None:
        if len(self.panel_widgets) > 1:
            new_tab = (self.current_tab - 1) % len(self.panel_widgets)
            self._switch_tab(new_tab)

    def action_submit(self) -> None:
        self._do_submit()

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())

    def _do_submit(self) -> None:
        answers = []
        for panel in self.panel_widgets:
            answer, is_other = panel.get_answer()
            answers.append((panel.question_data.question, answer, is_other))
        self.post_message(self.Answered(answers=answers))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in text input."""
        self._do_submit()

    def on_question_panel_cancel_requested(
        self, message: QuestionPanel.CancelRequested
    ) -> None:
        """Handle cancel request from panel."""
        self.post_message(self.Cancelled())
