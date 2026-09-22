from langchain_core.language_models import BaseChatModel

class Organizer:
    def __init__(
        self,
        organizer_model: BaseChatModel,
    ) -> None:
        self.organizer_model = organizer_model
