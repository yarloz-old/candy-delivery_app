# candy-delivery_app

candy-delivery_app - сервис, который помогает нанимать на работу курьеров, распределять заказы, расчитывать рейтинг курьеров и их заработок.

## Установка и запуск

```
sudo apt update
sudo apt install python3-pip python3-venv git tmux
sudo ufw allow 8080
git clone https://github.com/yarloz/candy-delivery_app.git
cd candy-delivery_app
python -m venv env
source env/bin/activate
pip install -r requirements.txt
tmux new -s candy-delivery_app
source env/bin/activate
gunicorn --bind 0.0.0.0:8080 wsgi:app
```

## Описание импортируемых пакетов

| Пакет | Ссылка и описание |
| ------ | ------ |
| flask | [https://pypi.org/project/Flask/][PlDb] |
|  | Основной фреймфорк |
| flask_restful | [https://pypi.org/project/Flask-RESTful/][PlGh] |
|  | Можно было бы обойтись без него. Использовал для сериализации объекта быза данных. |
| cerberus | [https://pypi.org/project/cerberus-python-client/][PlGd] |
|  | Использовал для валидации формата запроса. |
| flask_sqlalchemy | [https://pypi.org/project/Flask-SQLAlchemy/][PlOd] |
|  | База данных. |
| sqlalchemy | [https://pypi.org/project/SQLAlchemy/][PlMe] |
|  | Использовал функцию для формирования SQL запроса в виде строки. |
| pyrfc3339 | [https://pypi.org/project/pyRFC3339/][PlGa] |
|  | Использовал для генерации даты в формате RFC3339. |
| pytz | [https://pypi.org/project/pytz/][PlGa] |
|  | Использовал для получения локального времени. |

## Примечания

Было принято считать заказ подходящим по времени, если есть пересечение хотя бы одного из интервалов доставки и работы курьра. Два интервала пересекаются, если StartA < EndB и EndA > StartB.

