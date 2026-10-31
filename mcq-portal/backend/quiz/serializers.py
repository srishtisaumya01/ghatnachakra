from rest_framework import serializers


class AnswerSerializer(serializers.Serializer):
    qid = serializers.CharField(max_length=40)
    chosen = serializers.RegexField(r'^[a-e]$', allow_null=True, required=False, allow_blank=True)
    flagged = serializers.BooleanField(required=False, default=False)
    secs = serializers.FloatField(required=False, default=0, min_value=0, max_value=36000)


class MarkingSerializer(serializers.Serializer):
    correct = serializers.FloatField(min_value=0, max_value=10, default=1)
    negative = serializers.FloatField(min_value=0, max_value=10, default=0)


class ConfigSerializer(serializers.Serializer):
    marking = MarkingSerializer(required=False, default=dict)
    minutes = serializers.IntegerField(min_value=0, max_value=1000, required=False, default=0)


class AttemptCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, allow_blank=True, default='Practice test')
    duration = serializers.FloatField(min_value=0, max_value=200000, default=0)
    config = ConfigSerializer(required=False, default=dict)
    answers = AnswerSerializer(many=True, allow_empty=False, max_length=500)


def attempt_body(a):
    return {'id': a.pk, 'ts': a.created_at.timestamp(), 'name': a.name, 'config': a.config, 'duration': a.duration,
            'total': a.total, 'correct': a.correct, 'wrong': a.wrong, 'skipped': a.skipped, 'score': a.score, 'maxscore': a.maxscore}
