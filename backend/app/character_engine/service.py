from app.character_engine.loader import CharacterLoader
from app.character_engine.schemas import CharacterDefinition, RoleplayUserDefinition


class CharacterService:
    def __init__(self, loader: CharacterLoader | None = None) -> None:
        self.loader = loader or CharacterLoader()

    def list_characters(self) -> list[CharacterDefinition]:
        return self.loader.list_characters()

    def get_character(self, slug: str) -> CharacterDefinition:
        return self.loader.load_character(slug)

    def get_roleplay_user(self, slug: str) -> RoleplayUserDefinition:
        return self.loader.load_roleplay_user(slug)
