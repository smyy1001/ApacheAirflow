# Airflow 

## 1) Gereksinimler

* Docker & Docker Compose v2
* Boşta **8080** portu
* (Linux) İzinler için kendi UID/GID’nizi `.env` içinde ayarlamanız önerilir.

---

## 2) `.env` dosyasını ayarlayın

Proje kök dizininde bulunan `.env` dosyasını ihtiyacınıza göre doldurun.

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
BSky Trendler triggerdan sonra her 5 dk'de bir çalışır.

---

## 6) 🔍 Airflow’da Logları Görüntüleme (Son Sürüm)

Airflow 2.9+ sürümlerinde her task’in logları artık arayüzden doğrudan erişilebilir:

* DAGs sekmesinden ilgili DAG’i aç.

* Graph View veya Grid View’da task’in üstüne tıkla.

* Açılan pencerede “Logs” sekmesini seç.

> Gerekirse alt kısımda “Download Log File” ya da “View Raw Logs” düğmesini kullan.

💡 Eğer “Log not found” hatası alıyorsan, AIRFLOW__LOGGING__BASE_LOG_FOLDER ve AIRFLOW__CORE__REMOTE_LOGGING ayarlarını kontrol et.
