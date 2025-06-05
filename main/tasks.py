import httpx
from celery import shared_task
from decouple import config
from django.core.cache import cache


@shared_task
def update_exchange_rates():
    """
    Автоматически обновляет словарь, содержащий наименования валют и их обменный курс по отношению к российскому рублю.
    """
    url = f"https://v6.exchangerate-api.com/v6/{config('EXCHANGE_API_KEY')}/latest/RUB"
    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        cache.set('exchange_rates', data, timeout=60 * 60 * 24)
    except Exception as e:
        print(f'Ошибка обновления курса валют: {str(e)}')
