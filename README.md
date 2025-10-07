# Airflow 

## 1) Gereksinimler

* Docker & Docker Compose v2
* Boşta **8080** portu
* (Linux) İzinler için kendi UID/GID’nizi `.env` içinde ayarlamanız önerilir.

---

## 2) `.env` dosyasını ayarlayın

Proje kök dizininde bulunan `.env` dosyasını ihtiyacınıza göre doldurun.

```dotenv
# Airflow servisleri için (isteğe bağlı ama önerilir)
HOST_UID=1000
HOST_GID=0

# Uygulama çıktı klasörleri (host tarafında bu klasörler oluşturulur)
JSON_OUTPUT_DIR=bsky_data
LOG_OUTPUT_DIR=bsky_log

# Elasticsearch (API Key ile)
ES_BASE_URL=https://192.168.1.66:9200
# Aşağıdakilerden sadece birini kullanın:
# 1) Base64( id:api_key )
ES_API_KEY=ZHVtbXlJRDpkdW1teVNlY3JldA==
# 2) veya raw "id:api_key" (kod encode eder)
# ES_API_KEY=my_id:my_secret

# SSL
ES_VERIFY=false
ES_DISABLE_SSL_CERT_VALIDATION=false
# ES_CA_PATH=/etc/ssl/certs/custom-ca.pem

# Bsky scraper ayarları (örnek)
IDENTIFIER=onionbroccoli.bsky.social
PDS_HOST=https://bsky.social
QUERY=meclis
MAX_RESULTS=10
LANGUAGE=tr
```

> Not: Log/veri klasörleri host’ta `.env` içindeki isimlerle (örn. `bsky_log`, `bsky_data`) proje kökünde oluşturulur ve container içinde `/app/bsky_log`, `/app/bsky_data` olarak mount edilir.

---

## 3) Servisleri başlatın

```bash
docker compose up --build
```

Airflow UI şu adreste açılır:
[http://localhost:8080](http://localhost:8080)

* **Kullanıcı adı:** `airflow`
* **Şifre:** `airflow`

> Eğer ilk açılışta biraz bekletirse normaldir; scheduler & dag-processor senkronize olurken birkaç dakika sürebilir.

---

## 4) İlk kurulum: `bootstrao_es_for_media` DAG’ı

Airflow UI > **DAGs** sayfasında **`bootstrao_es_for_media`** isimli DAG’ı **bir kez** çalıştırın ve **bitmesini bekleyin**.
Bu işlem, Elasticsearch tarafındaki gerekli hazırlıkları/şemayı (index/policy vs.) yapar. **Sadece bir kere** çalıştırmanız yeterlidir.

---

## 5) Diğer DAG’ları çalıştırma

Kurulum DAG’ı tamamlandıktan sonra diğer DAG’ları **istediğiniz zaman** tetikleyebilirsiniz.

---

## 6) Çıktılar (log & data) nereye geliyor?

* Host’ta: `./bsky_log` ve `./bsky_data`
* Container içinde: `/app/bsky_log` ve `/app/bsky_data`

`docker compose` bind mount’ları otomatik oluşturacak şekilde ayarlanmıştır; klasör yoksa oluşturulur.

---