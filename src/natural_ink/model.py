"""Portable ink: page points, top-left origin, and full stroke widths in points."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Finite = Annotated[float, Field(allow_inf_nan=False)]
Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Point(StrictModel):
    x: Finite
    y: Finite
    width: Positive


class Stroke(StrictModel):
    points: list[Point] = Field(min_length=1)
    color: Color = "#42067a"


class InkPage(StrictModel):
    width: Positive = 612
    height: Positive = 792
    background: Color = "#faf9f1"
    strokes: list[Stroke] = Field(default_factory=list)

    @model_validator(mode="after")
    def within_page(self) -> InkPage:
        for stroke in self.strokes:
            for point in stroke.points:
                if not (0 <= point.x <= self.width and 0 <= point.y <= self.height):
                    raise ValueError("Stroke center lies outside the page")
        return self


class InkDocument(StrictModel):
    format: Literal["natural-ink/1"] = "natural-ink/1"
    title: str = "Natural Ink"
    provenance: str = "synthesized; not recorded pen history"
    pages: list[InkPage] = Field(min_length=1)


class TextItem(StrictModel):
    type: Literal["text"]
    text: str = Field(min_length=1)
    x: Finite
    y: Finite
    size: Positive = 18
    color: Color = "#42067a"


class SymbolItem(StrictModel):
    type: Literal["symbol"]
    symbol: str
    x: Finite
    y: Finite
    width: Positive = 16
    height: Positive = 16
    color: Color = "#42067a"


class RuleItem(StrictModel):
    type: Literal["rule"]
    x: Finite
    y: Finite
    length: Positive
    width: Positive = 1
    color: Color = "#42067a"


Item = Annotated[TextItem | SymbolItem | RuleItem, Field(discriminator="type")]


class LayoutPage(StrictModel):
    width: Positive = 612
    height: Positive = 792
    background: Color = "#faf9f1"
    grid: bool = True
    items: list[Item]


class Layout(StrictModel):
    title: str = "Natural Ink"
    pages: list[LayoutPage] = Field(min_length=1)
