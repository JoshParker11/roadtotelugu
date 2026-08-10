# Foundational Telugu

Foundational Telugu is a content-first, local-first project for building a structured Telugu learning path from an external grammar course, the learner's questions, and progressively richer practice.

The project has two connected aims:

1. Help the initial learner develop practical, culturally aware conversational Telugu for stronger relationships and cross-team work with colleagues and senior leaders in Hyderabad.
2. Turn the learning process into a reusable resource that can later help other people in the company.

The current source of truth is [LEARNING_GUIDE.md](LEARNING_GUIDE.md). It records the learning model, content workflow, site structure, phased roadmap, deferred ideas, and open decisions.

Open [index.html](index.html) for the course home. The first complete lesson is [Pronouns & the missing “to be”](lessons/lesson-01-pronouns.html), standalone question pages are indexed in the [deep-dive library](concepts/index.html), and controlled input lives in [Mini Stories](stories/index.html).

## Controlled input

The [known-language ledger](data/known-language.json) is the machine-readable source for story generation. Its readable website view is [stories/known-language.html](stories/known-language.html). It is not a duplicate of Anki: taught inflections may be grouped under a lexeme, while useful language introduced inside examples can still be recorded even without a standalone card.

- `introduced`: explicitly covered by a course lesson and eligible for controlled reuse
- `story_new`: the declared novelty budget for a particular story
- `bonus_exposure`: encountered elsewhere but not yet eligible for controlled stories
- `mastered`: learner-specific evidence; never inferred from lesson completion or Anki inclusion

At the foundation, a mini story targets roughly 90–95% controlled running tokens, introduces no more than one lexical item, and does not add an undeclared grammar pattern. Taught inflected forms count under their lexeme rather than as new vocabulary.

The first implementation is [Mini Story 01: Ravi and Sita](stories/story-01-ravi-and-sita.html). Its Telugu remains draft instructional content until reviewed and recorded by a proficient Telangana/Hyderabad speaker.

## Status

The course shell and first lesson are available as a local static website. No server or build step is required.

The evidence-informed acquisition roadmap that shaped the project is preserved at [archive/learning-research-roadmap.html](archive/learning-research-roadmap.html).

## Immediate next step

Review Lesson 1 and Mini Story 01, collect native-speaker corrections and audio for the story, and continue adding deep dives from genuine learner questions.