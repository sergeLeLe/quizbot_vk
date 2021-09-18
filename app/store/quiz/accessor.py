from typing import Optional

from app.base.base_accessor import BaseAccessor
from app.quiz.models import (
    Theme,
    Question,
    Answer,
    ThemeModel,
    QuestionModel,
    AnswerModel,
)
from typing import List


class QuizAccessor(BaseAccessor):
    async def create_theme(self, title: str) -> Theme:
        theme = await ThemeModel.create(title=title)
        return Theme(
            id=theme.id,
            title=theme.title
        )

    async def get_theme_by_title(self, title: str) -> Optional[Theme]:
        theme = await ThemeModel.query.where(ThemeModel.title == title).gino.first()
        return Theme(
            id=theme.id,
            title=theme.title
        ) if theme else None

    async def get_theme_by_id(self, id_: int) -> Optional[Theme]:
        theme = await ThemeModel.get(id_)
        return Theme(
            id=theme.id,
            title=theme.title
        ) if theme else None

    async def list_themes(self) -> List[Theme]:
        all_themes = await ThemeModel.query.gino.all()
        return [Theme(id=theme.id, title=theme.title) for theme in all_themes if theme]

    async def create_answers(self, question_id, answers: List[Answer]):
        for answer in answers:
            await AnswerModel.create(
                title=answer.title,
                is_correct=answer.is_correct,
                question_id=question_id
            )

    async def create_question(
        self, title: str, theme_id: int, answers: List[Answer]
    ) -> Question:
        question = await QuestionModel.create(
            title=title,
            theme_id=theme_id,
        )
        await self.create_answers(question.id, answers)
        return Question(
            id=question.id,
            title=question.title,
            answers=answers,
            theme_id=question.theme_id
        )

    async def get_question_by_title(self, title: str) -> Optional[Question]:
        question = await (
            QuestionModel.outerjoin(AnswerModel, QuestionModel.id == AnswerModel.question_id)
            .select()
            .where(QuestionModel.title == title)
            .gino
            .load(
                QuestionModel.distinct(QuestionModel.id).load(answers=AnswerModel.distinct(AnswerModel.id))
            )
            .all()
        )

        if not question:
            return None

        res = {
            **question[0].to_dict(),
            'answers': [e.to_dict() for e in question[0].answers]
        }

        return Question(
            id=res['id'],
            title=res['title'],
            answers=[Answer(is_correct=answer['is_correct'], title=answer['title']) for answer in res['answers']],
            theme_id=res['theme_id']
        )

    async def list_questions(self, theme_id: Optional[int] = None) -> List[Question]:
        questions = await (
                QuestionModel.outerjoin(AnswerModel, QuestionModel.id == AnswerModel.question_id)
                .select()
                .gino
                .load(
                    QuestionModel.distinct(QuestionModel.id).load(answers=AnswerModel.distinct(AnswerModel.id))
                )
                .all()
        )

        question_list = []
        await self._append_to_list_questions(questions, question_list)
        res_question_list = question_list[:]
        if theme_id:
            for question in res_question_list[:]:
                if question.theme_id != int(theme_id):
                    res_question_list.remove(question)
        return res_question_list

    async def _append_to_list_questions(self, questions, question_list):
        for question in questions:
            res = {
                **question.to_dict(),
                'answers': [e.to_dict() for e in question.answers]
            }
            question_list.append(
                Question(
                    id=res['id'],
                    title=res['title'],
                    answers=[Answer(is_correct=answer['is_correct'], title=answer['title']) for answer in res['answers']],
                    theme_id=res['theme_id']
                )
            )
