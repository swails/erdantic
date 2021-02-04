from typing import List, Set, Type

try:
    import pydantic
    import pydantic.fields
except ModuleNotFoundError:
    pass

from pydantic_erd.erd import Edge, Field, Model, register_constructor, EntityRelationshipDiagram


class PydandicField(Field):
    pydantic_field: "pydantic.fields.ModelField"

    def __init__(self, pydantic_field):
        if not isinstance(pydantic_field, pydantic.fields.ModelField):
            raise ValueError(
                "pydantic_field must be of type pydantic.fields.ModelField. "
                f"Got: {type(pydantic_field)}"
            )
        self.pydantic_field = pydantic_field

    @property
    def name(self) -> str:
        return self.pydantic_field.name

    @property
    def type_name(self) -> str:
        return self.pydantic_field._type_display()

    @property
    def type_obj(self) -> type:
        return self.pydantic_field.type_

    def is_many(self) -> bool:
        return self.pydantic_field.shape > 1

    def is_nullable(self) -> bool:
        return self.pydantic_field.allow_none

    def __hash__(self):
        return id(self.pydantic_field)


class PydanticModel(Model):
    pydantic_model: Type["pydantic.BaseModel"]

    def __init__(self, pydantic_model: Type["pydantic.BaseModel"]):
        if not isinstance(pydantic_model, type) or not issubclass(
            pydantic_model, pydantic.BaseModel
        ):
            raise ValueError(
                "pydantic_model must be a subclass of pydantic.BaseModel. "
                f"Received: {repr(pydantic_model)}"
            )
        self.pydantic_model = pydantic_model

    @property
    def name(self) -> str:
        return self.pydantic_model.__name__

    @property
    def fields(self) -> List[Field]:
        return [PydandicField(pydantic_field=f) for f in self.pydantic_model.__fields__.values()]

    def __hash__(self) -> int:
        return id(self.pydantic_model)


@register_constructor
def create_erd(*models: Type["pydantic.BaseModel"]) -> EntityRelationshipDiagram:
    seen_models = set()
    seen_edges = set()
    for model in models:
        search(model, seen_models, seen_edges)
    return EntityRelationshipDiagram(models=seen_models, edges=seen_edges)


def search(
    pydantic_model: pydantic.BaseModel, seen_models: Set[Model], seen_edges: Set[Edge]
) -> Model:
    model = PydanticModel(pydantic_model=pydantic_model)
    if model not in seen_models:
        seen_models.add(model)
        for field in model.fields:
            if issubclass(field.type_obj, pydantic.BaseModel):
                field_model = search(field.type_obj, seen_models, seen_edges)
                seen_edges.add(Edge(source=model, source_field=field, target=field_model))
    return model
