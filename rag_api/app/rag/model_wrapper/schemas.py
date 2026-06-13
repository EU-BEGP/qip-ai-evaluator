# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import List
from pydantic import BaseModel, Field, computed_field


class Issue(BaseModel):
    """One co-located finding: shortcoming + matching recommendation + deduction."""

    shortcoming: str
    recommendation: str
    deduction: float


class CriterionEvaluation(BaseModel):
    """Structured output for a single criterion evaluation."""

    Name: str
    Description: str = Field(..., description="Summary of the overall analysis")
    Issues: List[Issue] = Field(..., description="One entry per finding; empty list when criterion fully satisfied")

    @computed_field
    @property
    def Shortcomings(self) -> List[str]:
        return [i.shortcoming for i in self.Issues]

    @computed_field
    @property
    def Recommendations(self) -> List[str]:
        return [i.recommendation for i in self.Issues]

    @computed_field
    @property
    def Deductions(self) -> List[float]:
        return [i.deduction for i in self.Issues]


class BatchCriterionEvaluation(BaseModel):
    """Wrapper for a batch of criterion evaluations returned as a single JSON object."""

    evaluations: List[CriterionEvaluation]


class DocumentSnapshot(BaseModel):
    """Structured digest extracted verbatim from a module document."""

    Title: str = Field(..., description="Module title")
    Keywords: List[str] = Field(..., description="Keywords as a list of strings")
    Abstract: str = Field(..., description="Abstract section")
    IntendedLearningOutcomesKnowledge: str = Field(..., description="Learning outcomes: Knowledge")
    IntendedLearningOutcomesSkills: str = Field(..., description="Learning outcomes: Skills")
    IntendedLearningOutcomesResponsibility: str = Field(..., description="Learning outcomes: Responsibility")
    Outline: List[str] = Field(..., description="Ordered list of major sections/headings")
    ImportantInformation: List[str] = Field(
        ..., description="Verbatim sentences copied directly from the document — no paraphrasing"
    )


class ModuleMetadata(BaseModel):
    """Combined output from basic metadata + EQF level extraction prompts."""

    title: str = Field(..., description="The official title of the module")
    abstract: str = Field(..., description="Summary of the module content")
    uniqueness: str = Field(..., description="Explanation of what makes this module unique")
    societal_relevance: str = Field(..., description="How this module impacts society")
    elh: str = Field(..., description="Estimated Learning Hours (ELH) value")
    eqf: str = Field(..., description="European Qualification Framework (EQF) level")
    smcts: str = Field(..., description="SMCTS credit value")
    teachers: str = Field(..., description="Names and details of teachers/authors")
    keywords: List[str] = Field(..., description="List of keywords")
    suggested_knowledge: str = Field(..., description="Suggested EQF level for Knowledge ILO")
    suggested_skills: str = Field(..., description="Suggested EQF level for Skills ILO")
    suggested_ra: str = Field(..., description="Suggested EQF level for Responsibility and Autonomy ILO")
