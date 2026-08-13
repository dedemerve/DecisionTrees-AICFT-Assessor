# Metodoloji Taslağı — Computers & Education
# (Bölüm bölüm birlikte yazılıyor — v1)

---

## 3b. Ekran Kaydı Analizi (Screen Recording Analysis)

### 3b.1 Veri Toplama Altyapısı

Ekran kayıtları, araştırmacı tarafından bu çalışma için geliştirilen açık kaynaklı, web tabanlı bir uygulama aracılığıyla toplanmıştır (bkz. [GitHub deposu]). Uygulama, katılımcıların teknik arka plan gerektirmeden kaydı başlatıp bitirebileceği tek işlevli bir arayüzle sunulmuştur. Bu tasarım tercihi bilinçlidir: katılımcılar öğretmen adayları olup alan uzmanı değildir; arayüz karmaşıklığının veri kalitesini olumsuz etkilememesi için tüm teknik parametreler (codec, çözünürlük, örnekleme hızı, depolama hedefi) araştırmacı tarafından arka planda sabitlenmiştir. Kayıtlar tarayıcı üzerinden `.webm` formatında yerel olarak indirilmiş ve anonimleştirilmiş öğrenci kimlik kodlarıyla eşleştirilmiştir. Her kayıt tam oturumu kapsamaktadır; sahneleme veya seçici kayıt yapılmamıştır.

### 3b.2 Çok Kipli Öğrenme Analitiği (MMLA) Pipeline'ının Mimarisi

Toplanan kayıtlar, dört sıralı aşamadan oluşan çok kipli öğrenme analitiği (Multimodal Learning Analytics, MMLA) pipeline'ından geçirilmiştir. Her aşama bağımsız bir Python modülü olarak uygulanmış; aşamalar arası geçiş otomatikleştirilmiş ancak her aşamanın çıktısı sistematik insan doğrulamasına tabi tutulmuştur. Aşağıda her aşama ayrıntılı olarak açıklanmaktadır.

---

**Aşama 1 — Ses Katmanı: Hibrit Diyarizasyon**

İlk aşamada her kayıttaki ses verisi ayrı bir işleme zincirinden geçirilmiştir. Bu aşamanın iki alt işlevi vardır: konuşma tanıma (speech-to-text) ve konuşmacı rolü tanımlama (speaker diarization).

Konuşma tanıma için yerel MFCC tabanlı kümeleme algoritmasıyla ön işlem yapıldıktan sonra Whisper tabanlı transkripsiyon uygulanmıştır. Transkripsiyon çıktıları zaman damgalı segment listesi olarak kaydedilmiştir. Konuşmacı rolü tanımlama aşamasında her konuşma segmenti, araştırmacı tarafından derlenen öğretmen söylem örüntülerine (`TEACHER_PATTERNS`) dayalı bir skor hesaplama fonksiyonu aracılığıyla "öğretmen" veya "öğrenci" olarak etiketlenmiştir. Bu ayrım kritiktir: öğretmenin yönlendirme anları ile öğrencinin bağımsız çalışma anları, sonraki görsel değerlendirme aşamasında farklı ağırlıklara sahiptir.

Ses verisi bulunmayan veya sese dayalı bilginin anlamlı olmadığı oturumlar (`no_speech` durumu) otomatik olarak tespit edilmiş ve bu oturumlara ait görsel değerlendirmede ses bağlamı (argumentation_score) hesaplanmamıştır.

---

**Aşama 2 — Dinamik Kare Çıkarımı (Dynamic Frame Extraction)**

Tüm kayıt boyunca sabit frekansta kare çıkarmak hem hesaplama açısından verimsiz hem de analitik açıdan gürültülüdür: uzun süreli durağan ekran durumları ve geçiş hareketleri, anlamlı öğrenme davranışlarını temsil etmez. Bu nedenle sistematik bir hareket tabanlı seçim mekanizması benimsenmiştir.

Kare seçimi, piksel değişim yüzdesi eşiğine dayalı otomatik tetikleme mantığıyla çalışmaktadır. Bir kare ancak bir önceki kareden yeterli görsel farklılık gösterdiğinde çıkarılmakta; durağan ekran durumları atlanmaktadır. Bu mekanizma sayesinde her öğrenci oturumu için sabit bir kare sayısı değil, oturumun gerçek etkileşim yoğunluğuna orantılı bir kare kümesi elde edilmektedir. Her çıkarılan kareye ait saniye cinsinden zaman damgası, çıkarım tetikleme nedeni (`extraction_trigger_reason`) ve dosya yolu bir manifest dosyasına (`*_video_extraction_manifest.json`) kaydedilmiştir.

Sistem bellek doyumu veya kesinti kaynaklı hatalarda kaldığı yerden devam edebilecek şekilde tasarlanmıştır (auto-resume recovery). Kesinti sırasında tamamlanan kareler yeniden işlenmez; yalnızca kaldığı noktadan devam edilir. Bu özellik özellikle uzun oturumlar (15–25 dakika) için kararlılık açısından belirleyici olmuştur.

---

**Aşama 3 — Görsel Değerlendirme: Codebook-Grounded Multimodal Prompting**

Çıkarılan kareler, bir çok kipli büyük dil modeli (multimodal LLM) aracılığıyla yapılandırılmış davranış kodlarına dönüştürülmüştür. Bu aşama, çalışmanın analitik özgünlüğünü oluşturan temel bileşendir ve yöntem olarak **codebook-grounded multimodal prompting** olarak adlandırılmaktadır.

*Codebook'un oluşturulması.* 2025 öğretim yılında yürütülen önceki çalışmada, 17 öğrencinin ekran kayıtları uzman araştırmacı tarafından oturum başına saniye saniye izlenmiş ve her gözlem adımı serbest metin olarak kayıt altına alınmıştır. Bu 568 uzman anotasyonlu adım, CODAP Arbor ortamında gözlemlenebilecek öğrenci davranışlarının hem örüntü dağılımını hem de bağlamsal ayrımlarını ortaya koymuştur. Ayrıca CODAP Arbor arayüzünün hangi hareketlere olanak tanıdığı, hangi davranışların teknik olarak nasıl göründüğü, daha önce yayımlanmış çalışmalarda tanımlanmış temel kavramsal ve yazılım kullanım davranışları bu anotasyonlarla bütünleştirilmiştir.

*Davranış taksonomisi.* Bu birikimlerin sentezi olarak dokuz birincil davranış kodu tanımlanmıştır: `EXPLORE_DATA` (veri/grafik inceleme), `SELECT_TARGET` (hedef değişken seçimi), `BUILD_TREE` (karar ağacı inşası), `TUNE_THRESHOLD` (eşik ayarlama), `EVALUATE_MODEL` (model değerlendirme), `COMPARE_MODELS` (modeller arası karşılaştırma), `INTERPRET_RESULTS` (sonuç yorumlama), `IDLE_THINKING` (etkileşimsiz bekleme) ve `OFF_TASK` (görev dışı davranış). Her koda ek olarak ekran bağlamı (`screen_context`: TREE, GRAPH, TABLE, MIXED, MENU) ve öğrenme derinleştirme fazı (`deepen_phase`: SETUP, BUILDING, TUNING, EVALUATING, IDLE) alanları tanımlanmıştır.

*Sistem promptunun yapısı.* Bu taksonomi ve karar kuralları, yapılandırılmış bir sistem promptuna dönüştürülmüştür. Prompt altı adımlı bir öncelik hiyerarşisi içermektedir: (1) açık diyalog pencereleri ve menü durumları, (2) aktif ağaç inşası sinyalleri, (3) CTR (Classification Tree Records) panelinden karşılaştırma veya değerlendirme çıkarımı, (4) öncelik tablosunun uygulanması, (5) aktif inşa geçersiz kılma kuralı ve (6) frekans kalibrasyonu. Frekans kalibrasyonu, 2025 anotasyon verisinden türetilmiştir: örneğin `COMPARE_MODELS` davranışının görülme oranı %3 olarak sabitlenmiş; modelin bu davranışı %10'un üzerinde üretmesi durumunda yeniden değerlendirme gerekli kılınmıştır. Ayrıca görsel kanıt, her zaman ses veya log kaynağının üzerinde önceliklidir; gözlemlenemeyen durumlar için model `false` veya `null` üretmek zorundadır, asla çıkarım yapamaz.

*Çıktı formatı.* Her kare için model, birincil davranış, ikincil davranış (varsa), ekran bağlamı, derinleştirme fazı, görsel kanıt özeti ve değerlendirme güvenirlik durumu alanlarından oluşan yapılandırılmış bir JSON nesnesi üretmektedir. Bu nesne, log hizalamasında ve insan doğrulama sürecinde temel referans belgesi olarak kullanılmaktadır.

---

**Aşama 4 — Log–Video Hizalaması (Log–Video Alignment)**

Ekran kaydı analizi yalnızca görsel kanıta dayandığında bazı davranış türleri doğrudan gözlemlenemez veya güvenilir biçimde kodlanamaz. Bu sınırı aşmak için CODAP Arbor'ın ürettiği olay kayıt dosyaları (event log CSV) ile video kareler arasında zamana dayalı bir hizalama yapılmıştır.

Her oturum için elde edilen ham log dosyası 16 farklı eylem türü içermektedir. Bu eylemlerin yaklaşık %61,8'i analitik açıdan anlamlı değildir (arayüz durum değişiklikleri, sürükleme gürültüsü, oturum meta verisi). Filtreleme sonrası analitik açıdan anlamlı eylemler tutulmuştur: `emit_tree_data` (model gönderme), `drop_attribute` (özellik seçimi), `change_split_values` (eşik değiştirme), `change_tree_type`, `change_dataset` ve `data_context_change`.

Hizalama işleminde her log olayının zaman damgası, video kare manifestindeki en yakın kare zaman damgasıyla eşleştirilmiştir. Hizalanmış log olayları, ilgili karenin JSON çıktısına `synchronized_log_event` alanı olarak eklenmiştir. Bu sayede örneğin özellik seçimi (`drop_attribute`) logda görülüyorsa ve karşılık gelen karede bu seçim görsel olarak da doğrulanabiliyorsa, kanıt T1 güven kademesi olarak sınıflandırılmıştır. Log olay var ancak görsel kanıt doğrulanamıyorsa kanıt T2'ye düşürülmüştür. İki kaynağın da anlık hizalanmasında güvenilir bir zaman damgası bulunamıyorsa ordinal-orantılı bir sezgisel yöntem uygulanmış ve bu durum `alignment_method` alanında `ordinal_proportional_heuristic` olarak işaretlenmiştir.

Elde edilen bütünleşik kayıtlar, öğrenci başına üç Parquet dosyası olarak dışa aktarılmıştır: oturum düzeyinde (`*_session_ml_features.parquet`), episode düzeyinde (`*_episodes.parquet`) ve davranış kodu düzeyinde (`*_episode_process_codes.parquet`). Bu tablolar, hem makine öğrenmesi özellik vektörleri hem de nitel süreç analizi için kullanıma hazır biçimdedir.

---

> **[Devam edecek — 3b.3 İnsan Doğrulama Protokolü → Bölüm 4'e taşınacak]**

---

## 3d. Jupyter Notebook Analizi (Dönem Sonu Proje Ödevi)

### Veri Bağlamı ve Kapsam

Öğrencilerden dönem sonu bireysel proje ödevi kapsamında bağımsız bir karar ağacı analizi gerçekleştirmeleri ve bu süreci belgelendiren bir Jupyter notebook teslim etmeleri beklenmiştir. Öğrenciler veri setini ve problem bağlamını kendileri belirlemiş; not almak, açıklama yazmak ve kodu adım adım çalıştırmak için notebook ortamını kullanmışlardır. On dört öğrenci `.ipynb` formatında notebook teslim etmiştir. Bu notebook'lar ev ortamında bağımsız olarak üretilmiş olup herhangi bir ekran kaydı veya log verisiyle eşleştirilmemiştir; analiz yalnızca teslim edilen dosya içeriğine dayanmaktadır.

Bu ödev bağlamı, AI-CFT çerçevesinin üçüncü boyutunda tanımlanan en üst yetkinlik düzeyine karşılık gelmektedir. CODAP Arbor oturumlarında öğrenciler araştırmacı tarafından belirlenen bir veri seti üzerinde görsel bir arayüzle çalışmıştır. Proje ödevinde ise öğrenciler hem problemi hem de aracın nasıl kullanılacağını bağımsız olarak tanımlamıştır. Bu geçiş, LO3.3.2 (tool_customisation) ve LO3.3.3 (self_defined_test_criteria) yetkinlikleriyle ilişkilendirilmektedir.

### Aşama 1 — Notebook Yapısının Ayrıştırılması

Toplanan `.ipynb` dosyaları JSON formatında içe alınmıştır. Her notebook için hücre dizisi çıkarılmış ve hücre türüne göre sınıflandırılmıştır: kod hücresi ve markdown hücresi. Kod hücrelerinden çalıştırma sayısı (`execution_count`), kaynak kod içeriği ve çıktı nesneleri (standart çıktı, hata çıktısı, görsel çıktı) ayrıştırılmıştır. Her notebook için hücre türü dağılımı, toplam hücre sayısı ve hata içeren hücrelerin varlığı kayıt altına alınmıştır.

### Aşama 2 — Çalıştırma Dizisi Analizi

Her notebook için hücre çalıştırma sırası `execution_count` değerleri üzerinden yeniden oluşturulmuş ve çalıştırma dizisinin sıralı olup olmadığı incelenmiştir. Çalıştırma sayılarının doğrusal olmayan örüntüler sergilemesi —sonraki bir hücrenin daha düşük `execution_count` taşıması ya da belirli hücrelerin tekrar çalıştırılmış olması— öğrencinin notebook'u doğrusal bir akışla değil, bölümler arasında gidip gelerek ürettiğine işaret etmektedir. Bu örüntü, öğrencinin analiz sürecinde geri dönerek düzeltme yaptığının ya da hücreleri farklı bir sırayla keşfettiğinin kanıtı olarak değerlendirilmiştir.

### Aşama 3 — İçerik Doğrulaması ve AI-CFT Eşleştirmesi

Her notebook'ta karar ağacı uygulamasının gerçekleştirilip gerçekleştirilmediği kod hücrelerinin içeriği incelenerek doğrulanmıştır. Doğrulama kapsamında şu unsurlar aranmıştır: veri yükleme ve ön işleme adımları, `DecisionTreeClassifier` ya da eşdeğer bir model nesnesinin tanımlanması, eğitim ve test bölünmesi, model eğitimi ve performans değerlendirmesi. Bu adımların notebook'ta sıralı ve çalıştırılmış biçimde bulunması, öğrencinin süreci anlayarak uyguladığının yapısal kanıtı olarak alınmıştır.

Elde edilen veriler AI-CFT yetkinlik çerçevesiyle eşleştirilmiştir. Bağımsız veri seti seçimi ve problem tanımı LO3.3.3 ile, kütüphane parametrelerinin özelleştirilmesi ve yorumlanması ise LO3.3.2 ile ilişkilendirilmiştir. Bu eşleştirme, CODAP oturumlarından elde edilen davranış kodu verileriyle birlikte her öğrencinin AI-CFT profili içinde değerlendirilmiştir.

### Aşama 4 — Araştırmacı Doğrulaması

Otomatik ayrıştırmadan elde edilen yapısal özellikler —hücre sayısı, hata varlığı, çalıştırma sırası, temel bileşenlerin varlığı— araştırmacı tarafından kaynak dosyayla karşılaştırılarak doğrulanmıştır. İçerik doğrulaması aşamasında otomatik tespitin yetersiz kaldığı durumlar —eksik teslim, boş hücre, çalıştırılmamış kod— araştırmacı tarafından tek tek işaretlenmiş ve kayıt altına alınmıştır.

---

## 3c. Event Log İşleme (Keşif Davranışı Analizi)

Log dosyaları, Bölüm 3b'de açıklanan video hizalama işlevine ek olarak bağımsız bir analitik kaynak olarak da kullanılmıştır. Bu bölümde açıklanan analizler yalnızca log verisi üzerinden yürütülmüş; hiçbir video karesi veya ses verisi devreye girmemiştir. CODAP Arbor oturum log dosyaları, öğrencinin her model gönderimindeki parametre tercihlerini ve doğruluk değerini zaman sırasıyla kayıt altına almaktadır. Bu yapı, öğrencinin keşif sürecini —hangi sırayla, hangi parametrelerle, ne sıklıkta deneme yaptığını— yeniden oluşturmaya olanak tanımaktadır.

### Emit Dizisinin Oluşturulması

Her öğrenci oturumu için filtrelenmiş log akışı zaman damgasına göre sıralanmış ve emit dizisi çıkarılmıştır. Emit dizisi; sıralı model gönderimlerinin listesini, her gönderimde elde edilen doğruluk değerini ve gönderimler arası parametre değişikliklerini içermektedir. Bu diziden aşağıdaki oturum düzeyi özellikler türetilmiştir: toplam emit sayısı, ilk gönderime kadar geçen süre (time-to-first-emit), son gönderimde elde edilen doğruluk değeri, doğruluk yörüngesi boyunca hesaplanan standart sapma (accuracy volatility) ve gönderimler arası özellik değişim sayısı (feature change count). Bu özellikler `*_log_process_metadata.json` dosyasındaki `task4_process_variables` alanına kaydedilmiş ve makine öğrenmesi analizlerinde oturum düzeyi girdi olarak kullanılmıştır.

### B15 — Sistematik Parametre Keşfi (VOTAT Oranı)

Emit dizisinden türetilen temel davranışsal ölçüm, sistematik parametre keşfi davranışını temsil eden VOTAT (Vary One Thing At a Time) oranıdır. Bu oran, ardışık iki emit arasında yalnızca tek bir parametrenin değiştirildiği aralıkların tüm aralıklara oranı olarak tanımlanmaktadır. VOTAT oranı yüksek olan öğrenciler her denemede yalnızca bir değişkeni sistematik olarak denemiş; düşük VOTAT oranı ise aynı anda birden fazla parametreyi değiştirme örüntüsüne, yani daha az kontrollü bir keşif stratejisine işaret etmektedir. Bu ölçüm, AI-CFT çerçevesinin üçüncü boyutunda tanımlanan LO3.2.1 (proficient_independent_operation) yetkinliğiyle ilişkilendirilmiştir.

VOTAT oranı tamamen log kayıtlarından algoritmik olarak hesaplanmıştır. Bu ölçüm için insan video kodlaması yapılmamıştır; tek bir video karesinde VOTAT davranışı gözlemlenemeyeceğinden kare düzeyinde doğrulama metodolojik olarak uygun değildir. Bu sınırlılık yayın dilinde açıkça belirtilmiştir: "VOTAT oranı (B15), CODAP Arbor event log kayıtlarından algoritmik olarak hesaplanmıştır. Kare düzeyinde veya episode düzeyinde insan doğrulaması yapılmamıştır."

### B16 — Hata Kurtarma ve Uyarlanabilir Düzeltme

Log dizisinden tespit edilen ikinci süreç davranışı hata kurtarmadır. Bu davranış, Classification Tree Records panelinden bir kaydın silinmesinin ardından farklı bir tahmin değişkeniyle yeniden ağaç oluşturma dizisinin log'da gözlemlenmesiyle tespit edilmektedir: `DELETE_TREE_OR_CTR_ROW` → `DRAG_SPLIT_ATTRIBUTE` (farklı tahmin değişkeni). Bu dizi öğrencinin düşük performanslı bir modeli yalnızca eşiği ayarlayarak düzeltmeye çalışmak yerine tahmin değişkenini değiştirerek daha derin bir teşhis yaptığına işaret etmektedir. Bu davranış AI-CFT çerçevesindeki LO3.2.3 (transferable_problem_solving) yetkinliğiyle ilişkilendirilmiştir.

B16 tespiti algoritmik olarak gerçekleştirilmiştir. Bu süreç davranışı için bağımsız insan doğrulaması yapılmamıştır. Söz konusu sınırlılık yayın dilinde açıkça belirtilmiştir: "B16 ve B17 süreç davranışları video analizi ile kodlanmış olmakla birlikte insan kodlama düzeyinde güvenirlik analizi gerçekleştirilmemiştir."

### Araştırmacı Doğrulaması

Log kaynaklı davranışsal ölçümler için araştırmacı doğrulaması iki düzeyde gerçekleştirilmiştir. Birinci düzeyde emit dizisinin doğruluğu, 3b bölümünde açıklanan çapraz doğrulama protokolü çerçevesinde video karelerindeki görsel kanıtla karşılaştırılmıştır. İkinci düzeyde VOTAT ve B16 hesaplamalarının ham log verisiyle tutarlılığı araştırmacı tarafından örnekleme yoluyla kontrol edilmiştir. Algoritmik tespitlerin tamamının bağımsız insan doğrulamasından geçirilmediği bu çalışmada şeffaflık, metodolojik bir zorunluluk olarak değerlendirilmiş ve her ölçüm için tespit kaynağı ile doğrulama düzeyi ayrı ayrı raporlanmıştır.

---

## 3a. Çalışma Yaprağı Skorlaması (OCR Tabanlı)

Çalışmada öğrencilere üç haftalık öğretim süreci boyunca on bir çalışma yaprağı uygulanmıştır: WS1, WS3, WS4, WS5, WS6, WS7, WS10, WS11, WS_DT, WS_DT_INTRO ve WS_DT_XENO. Bu çalışma yaprakları öğrencilere fiziksel kağıt biçiminde dağıtılmış, doldurulduktan sonra taranmış ve dijital görüntü olarak işleme alınmıştır. Toplam 270 yanıt alanı içeren bu belgeler, yanıt formatları bakımından belirgin biçimde farklılaşmaktadır: çoktan seçmeli, kısa sayısal yanıt, el yazısıyla doldurulmuş karar ağacı diyagramları, operatör ifadeleri (örn. `Yağ ≤ 4,0`), karışıklık matrisi hesaplamaları ve Likert ölçekli değerlendirme soruları bir arada yer almaktadır. Bu çeşitlilik, tek tip bir değerlendirme yönteminin kullanılmasını olanaksız kılmış; yanıt alanının yapısına göre farklılaştırılmış bir işleme ve skorlama mimarisi geliştirilmesini zorunlu kılmıştır.

### Pipeline Grupları

Yanıt alanları, doğru yanıtın niteliğine göre iki işleme grubuna ayrılmıştır.

*Grup A — LLM Destekli Skorlama:* WS1, WS3, WS4, WS10, WS11, WS_DT, WS_DT_INTRO ve WS_DT_XENO bu gruba dahildir. Bu çalışma yapraklarındaki yanıtlar yorumlayıcı, eşdeğerlik veya kavramsal değerlendirme gerektiren niteliktedir. Örneğin öğrencinin bir karar ağacı eşiğini neden seçtiğini açıkladığı serbest metin yanıtları ya da enerji tablosundaki misclassification sayılarını yorumladığı alanlar bu gruba girmektedir. Bu tür yanıtlar otomatik eşleştirme mantığıyla değil, AI-CFT çerçevesi ve araştırmacı tarafından geliştirilen rubrik esas alınarak büyük dil modeli aracılığıyla skorlanmıştır.

*Grup B — Deterministik Python Skorlaması:* WS5, WS6 ve WS7 bu gruba dahildir. Bu çalışma yapraklarında doğru yanıt, referans veri kümesinden (11 gıda kartı içeren `prodabi_food_cards.csv`) hesaplama yoluyla türetilebilmektedir. Operatör ifadelerinin mantıksal tutarlılığı, misclassification oranlarının doğruluğu ve çapraz çalışma yaprağı tutarlılığı (WS7'nin WS6 ağacına dayalı doğrulaması) Python modülleri tarafından otomatik olarak hesaplanmıştır. Bu grupta büyük dil modeli yalnızca metin çıkarımı için kullanılmış, skorlama kararı tamamen deterministik Python mantığına bırakılmıştır.

### Aşama 1 — Tarama ve Sayfa Düzeni Ayrıştırma

Taranan çalışma yaprakları çok sayfalı görüntü olarak alınmış ve her sayfada yanıt alanlarının koordinatları çalışma yaprağına özgü ROI (region-of-interest) manifestleri aracılığıyla belirlenmiştir. Tablo içeren çalışma yapraklarında (WS5, WS6, WS10) satır ve sütun sınırları çizgi algılama sezgiselleriyle tespit edilerek her hücre ayrı bir görüntü olarak kırpılmıştır. Bu işlem özellikle WS10 için kritik öneme sahiptir: tablodaki sütun konumu anlamsal kimliği kodlamaktadır ve B1–B8 referans yanıtlarıyla eşleşmenin doğru gerçekleşebilmesi için hücre konumunun korunması zorunludur.

### Aşama 2 — OCR ve El Yazısı Tanıma

Kırpılan her yanıt alanı, görsel yeteneklere sahip bir büyük dil modeline yapılandırılmış bir çıkarım istemi ile sunulmuştur. İstem; alan tanımlayıcısını, beklenen yanıt biçimini (operatör ifadesi, sayısal değer, serbest metin, çoktan seçmeli) ve bilinen kısıtlamaları (örn. "operatör yalnızca ≤, <, ≥, > sembollerinden biri olmalıdır") içermiştir. Baskılı metinler için standart OCR, el yazılı alanlar için el yazısı tanıma (HTR) uygulanmıştır. Ham transkripsiyon çıktısı `extraction.json` dosyasında değiştirilmeden saklanmıştır; tüm sonraki işlemler bu ham veri üzerinden yürütülmüştür.

### Aşama 3 — Mekanik Normalleştirme

Çıkarım sonrası, yaygın OCR hatalarını gidermek amacıyla kural tabanlı bir normalleştirme aşaması uygulanmıştır. Bu aşamada gerçekleştirilen düzeltmeler tamamen mekanik niteliktedir ve anlamsal değerlendirme içermemektedir: operatör karakter dönüşümleri (`=<` → `≤`, `=>` → `≥`), sayısal alanlarda ondalık ayırıcı standardizasyonu (virgül → nokta) ve büyük/küçük harf normalizasyonu bu işlemler arasında yer almaktadır. Ham `extraction.json` değiştirilmemiş; normalleştirilmiş veri yalnızca doğrulama ve skorlama aşamalarında kullanılmıştır.

### Aşama 4 — Doğrulama ve Skorlama

Grup B çalışma yaprakları için Python doğrulama modülleri her yanıt alanını referans veri kümesiyle karşılaştırarak tutarlılık kontrolü yapmıştır. WS5 doğrulaması; operatör geçerliliğini, eşik aralığını, bölme sayılarının toplamını (11 kart), tamamlayıcı operatör çiftlerini ve misclassification oranı tutarlılığını denetlemiştir. WS7 doğrulaması ise öğrencinin kendi WS6 ağacıyla çapraz referans gerektirmiş; bu nedenle WS7 işlenmeden önce WS6 çıkarımının tamamlanması zorunlu koşul olarak belirlenmiştir.

Grup A çalışma yaprakları için rubrik değerlendirmesi iki kaynağa dayanmaktadır. Birincisi, araştırmacı tarafından 2025 kohort verilerinden geliştirilen ve doğru/yanlış etiketlerini içeren cevap anahtarı ve codebook'tur. İkincisi, UNESCO AI Competency Framework for Teachers (AI-CFT) dokümanıdır. Bu iki kaynak, her yanıt alanı için beklenen performans ölçütlerini tanımlayan rubrik dosyalarına dönüştürülmüştür. Büyük dil modeli, normalleştirilmiş çıkarım çıktısını ve rubrik kriterlerini birlikte alarak madde skoru, karşılanan rubrik ölçütü ve en az 10 karakter uzunluğunda bir kanıt alıntısı üretmiştir. Modelin sayısal toplam hesaplaması yapması açıkça yasaklanmıştır; toplam skor hesabı tüm madde skorları alındıktan sonra Python biriktiricisi tarafından gerçekleştirilmiştir.

### DT Serisi Çalışma Yaprakları için Özel Skorlama Protokolü

Öğretim sürecinde kullanılan DT serisi çalışma yaprakları ek bir metodolojik dikkat gerektirmektedir.

WS_DT_INTRO (80 boşluk) iki bölümden oluşmaktadır. Birinci bölüm olan Xeno (ague) etkinliğinde her öğrenciye rastgele üretilen bağımsız bir vaka seti dağıtılmıştır. Kök düğüm hasta yüzdesi, sınıflandırma matrisi değerleri ve performans metrikleri öğrenciden öğrenciye farklılık gösterdiğinden bu bölüm için evrensel bir cevap anahtarı oluşturulması mümkün değildir. Bu nedenle Xeno bölümünün sayısal alanları, sabit bir anahtarla değil, öğrencinin kendi ağacından türetilebilen değişmez yapısal özelliklerle karşılaştırılarak iç tutarlılık üzerinden puanlanmıştır. Bu yapısal özellikler arasında FP=0, FN=0, TP+TN=N bağıntısı ve doğruluk=%100 koşulları yer almaktadır; saç rengi Xeno veri setinde hedef değişkeni kusursuz ayırdığından bu değerler veri setinden bağımsız olarak değişmezdir. İkinci bölüm olan Titanic etkinliğinde ise tüm öğrencilere aynı veri seti dağıtılmıştır. Bu bölümdeki sayısal değerler CSV'den hesaplanan kanonik değerlere karşılaştırılmış ve öğrencilerin CODAP ağacından elle okumasından kaynaklanan küçük yuvarlama farklılıklarını karşılamak amacıyla ±%2 tolerans uygulanmıştır.

WS_DT_XENO (33 boşluk) ise yalnızca Xeno etkinliğini kapsayan bağımsız bir çalışma yaprağıdır. Karışıklık matrisi bileşenlerini, performans metriklerini (doğruluk, duyarlılık, özgüllük, kesinlik) ve misclassification oranı hesaplamalarını içermekte olup yukarıda açıklanan iç tutarlılık protokolü bu çalışma yaprağına da uygulanmıştır.

### Araştırmacı Doğrulaması

Büyük dil modelinin ürettiği tüm çıkarım ve skorlama çıktıları araştırmacı tarafından tek tek incelenmiştir. Modelin hatalı transkribe ettiği yanıtlar, yanlış sınıflandırdığı operatör ifadeleri veya rubrik ölçütlerini yanlış uyguladığı durumlar doğrudan düzeltilmiştir. Bu süreçte otomasyon, araştırmacının 270 yanıt alanını her öğrenci için sistematik biçimde gözden geçirebilmesi amacıyla bir yapılandırma ve ön işleme mekanizması olarak konumlandırılmıştır. İnsan değerlendirme psikolojisinin tutarsızlıklar üretme olasılığı — yorgunluk, sıralama etkileri ve öğrenci kimliğine ilişkin farkındalık — bu mimarinin tasarım gerekçelerinden birini oluşturmaktadır: büyük dil modeli her yanıtı bağımsız ve tutarlı biçimde işlerken nihai karar yetkisi araştırmacıda kalmıştır.
