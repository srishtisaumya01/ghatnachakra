import re

from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.errors import ApiError, not_found, validation_error

from . import catalog, crops, services
from .models import Attempt, AttemptItem
from .serializers import AttemptCreateSerializer, attempt_body

DATA_PATH = re.compile(r'^(manifest\.json|q/[a-z]+-\d{3}\.json)$')


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'ok': True})


class PublicStatsView(APIView):
    """Counts for the public landing page (no question text)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        response = Response(catalog.public_stats())
        response['Cache-Control'] = 'public, max-age=300'
        return response


class DataView(APIView):
    """The manifest and the chapter files: only for signed-in users."""

    def get(self, request, path):
        if not DATA_PATH.match(path):
            raise not_found()
        file = (catalog_dir() / path)
        if not file.is_file():
            raise not_found()
        response = FileResponse(file.open('rb'), content_type='application/json')
        response['Cache-Control'] = 'private, max-age=600'
        return response


def catalog_dir():
    from django.conf import settings

    return settings.DATA_DIR


class CropView(APIView):
    def get(self, request):
        book = request.query_params.get('book', '')
        if book not in catalog.manifest()['books']:
            raise not_found()
        try:
            segs = crops.clean_segments(request.query_params.get('segs', ''))
            png = crops.crop_png(book, segs)
        except crops.BadCrop:
            raise validation_error('That crop is not valid.')
        except FileNotFoundError:
            raise ApiError('books_missing', 'The source book is not available on this server.', 503)
        response = HttpResponse(png, content_type='image/png')
        response['Cache-Control'] = 'private, max-age=86400'
        return response


class AttemptListView(APIView):
    def get(self, request):
        return Response([attempt_body(a) for a in Attempt.objects.filter(user=request.user).order_by('-created_at', '-pk')])

    def post(self, request):
        data = AttemptCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        attempt = services.evaluate(request.user, d['name'] or 'Practice test', d['duration'], d['config'], d['answers'])
        if attempt.total == 0:
            attempt.delete()
            raise validation_error('None of those questions are in the question bank.')
        return Response({'id': attempt.pk}, status=status.HTTP_201_CREATED)


class AttemptDetailView(APIView):
    def _get(self, request, pk):
        attempt = Attempt.objects.filter(user=request.user, pk=pk).first()
        if attempt is None:
            raise not_found()
        return attempt

    def get(self, request, pk):
        attempt = self._get(request, pk)
        items = attempt.items.order_by('pk').values('qid', 'chapter', 'subject', 'chosen', 'answer', 'status', 'flagged', 'secs')
        return Response({**attempt_body(attempt), 'items': list(items)})

    def delete(self, request, pk):
        self._get(request, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuestionStatsView(APIView):
    """Per question: how often it was answered right/wrong by this user, and the result of the latest attempt."""

    def get(self, request):
        items = AttemptItem.objects.filter(attempt__user=request.user)
        rows = items.values('qid').annotate(n=Count('pk'), c=Count('pk', filter=Q(status='correct')), w=Count('pk', filter=Q(status='wrong')))
        latest = {}
        for qid, st in items.order_by('attempt_id').values_list('qid', 'status'):  # later attempts overwrite earlier ones
            latest[qid] = st
        return Response({r['qid']: {'n': r['n'], 'c': r['c'], 'w': r['w'], 'last': latest.get(r['qid'])} for r in rows})
