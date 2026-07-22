from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PublicStatus(str, Enum):
    REVISE_AND_RESUBMIT = "revise_and_resubmit"
    UNDER_REVIEW = "under_review"
    PREPARING_RESUBMISSION = "preparing_resubmission"
    IN_PREPARATION = "in_preparation"
    RESEARCH_IN_PROGRESS = "research_in_progress"


class Link(StrictModel):
    label: str = Field(min_length=1)
    url: HttpUrl


class Profile(StrictModel):
    name: str
    title: str
    institution: str
    location: str
    email: str
    website: str
    portrait_alt: str | None = None
    positioning: str
    short_positioning: str
    links: list[Link] = Field(default_factory=list)


class Appointment(StrictModel):
    id: str
    institution: str
    role: str
    start_year: int
    end_year: int | None = None


class Education(StrictModel):
    id: str
    institution: str
    degree: str
    year: int
    details: list[str] = Field(default_factory=list)


class Publication(StrictModel):
    id: str
    category: Literal["journal", "conference"]
    citation_html: str
    title: str
    authors: list[str]
    year: int
    journal: str
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    author_note: str | None = None
    links: list[Link] = Field(default_factory=list)


class Presentation(StrictModel):
    id: str
    kind: Literal["invited_talk", "conference_presentation"]
    year: int
    title: str
    venue: str
    date: str | None = None
    source_key: str | None = None


class TeachingRecord(StrictModel):
    id: str
    institution: str
    course: str
    level: str
    terms: list[str]
    role: str | None = None
    source_key: str | None = None


class StudentRecord(StrictModel):
    id: str
    name: str
    program: str
    institution: str
    role: str
    placement: str | None = None


class IndustryRecord(StrictModel):
    id: str
    organization: str
    years: str
    role: str
    description: str | None = None


class MediaMention(StrictModel):
    id: str
    outlet: str
    title: str
    format: str
    date: str | None = None
    url: HttpUrl
    related_work_ids: list[str] = Field(default_factory=list)


class Award(StrictModel):
    id: str
    title: str
    year: int | None = None
    amount: str | None = None
    related_work_ids: list[str] = Field(default_factory=list)
    source_key: str | None = None


class ServiceRecord(StrictModel):
    id: str
    role: str
    organization: str | None = None
    details: str | None = None


class TechnicalStrength(StrictModel):
    category: str
    items: list[str]


class LanguageRecord(StrictModel):
    language: str
    proficiency: str


class PublicProfile(StrictModel):
    profile: Profile
    appointments: list[Appointment]
    education: list[Education]
    research_interests: list[str]
    publications: list[Publication]
    presentations: list[Presentation]
    teaching: list[TeachingRecord]
    students: list[StudentRecord]
    industry: list[IndustryRecord]
    professional_services: str | None = None
    media: list[MediaMention]
    awards: list[Award]
    service: list[ServiceRecord]
    technical_strengths: list[TechnicalStrength]
    languages: list[LanguageRecord]


class PublicProject(StrictModel):
    id: str
    title: str
    authors: list[str] = Field(min_length=1)
    status: PublicStatus
    journal: str | None = None
    summary: str = Field(min_length=20)
    links: list[Link] = Field(default_factory=list)
    featured: bool
    order: int
    last_verified: str

    @model_validator(mode="after")
    def validate_journal_visibility(self) -> PublicProject:
        journal_required = {
            PublicStatus.REVISE_AND_RESUBMIT,
            PublicStatus.UNDER_REVIEW,
            PublicStatus.PREPARING_RESUBMISSION,
        }
        if self.status in journal_required and not self.journal:
            raise ValueError("journal is required for this public status")
        if self.status not in journal_required and self.journal:
            raise ValueError("work with this public status must omit journal")
        draft_markers = {
            "draft title for replacement",
            "short outward-facing description",
            "replace this copy",
            "lorem ipsum",
        }
        if self.title.lower() in draft_markers or self.summary.lower() in draft_markers:
            raise ValueError("draft copy cannot be published")
        return self


class PublicSnapshot(StrictModel):
    schema_version: Literal[1] = 1
    profile: PublicProfile
    projects: list[PublicProject]

    @model_validator(mode="after")
    def validate_ids_and_relationships(self) -> PublicSnapshot:
        records = [
            *self.profile.appointments,
            *self.profile.education,
            *self.profile.publications,
            *self.profile.presentations,
            *self.profile.teaching,
            *self.profile.students,
            *self.profile.industry,
            *self.profile.media,
            *self.profile.awards,
            *self.profile.service,
            *self.projects,
        ]
        ids = [record.id for record in records]
        duplicates = sorted({record_id for record_id in ids if ids.count(record_id) > 1})
        if duplicates:
            raise ValueError(f"duplicate public IDs: {duplicates}")
        work_ids = {
            publication.id for publication in self.profile.publications
        } | {project.id for project in self.projects}
        for relation in [*self.profile.media, *self.profile.awards]:
            unknown = set(relation.related_work_ids) - work_ids
            if unknown:
                raise ValueError(
                    f"{relation.id} references unknown public work IDs: {sorted(unknown)}"
                )
        return self
