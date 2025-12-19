Ajan Tabanlı Yapay Zeka ve Bilişsel Mimarilerde Yeni Ufuklar: Kapsamlı Literatür Taraması ve Analitik Rapor
1. Yönetici Özeti ve Giriş
Yapay Zeka (YZ) araştırmalarının son dönemdeki yörüngesi, statik dil modellerinden (LLM - Large Language Models), çevreleriyle etkileşime girebilen, plan yapabilen ve kendi çıktılarını düzeltebilen "Agentic AI" (Ajan Tabanlı YZ) sistemlerine doğru dramatik bir kayma göstermektedir. Bu rapor, arXiv, NeurIPS, OpenReview ve MDPI gibi önde gelen akademik platformlarda yayınlanan ve Ajan Tabanlı YZ, akıl yürütme (reasoning), çoklu ajan işbirliği ve kendi kendini doğrulama mekanizmaları üzerine odaklanan kritik araştırmaları derinlemesine incelemektedir.

İncelenen literatür, LLM'lerin sadece birer "sonraki kelime tahmincisi" olmaktan çıkıp, karmaşık problemleri çözebilen "Bilişsel Motorlara" dönüştüğünü ortaya koymaktadır. Özellikle ReAct  gibi erken dönem çalışmalarla başlayan "akıl yürütme ve eylemi birleştirme" vizyonu, ReWOO  ile verimlilik odaklı modüler mimarilere, Reflexion  ile hafıza tabanlı öğrenmeye ve Mixture-of-Agents (MoA)  ile kolektif zekaya evrilmiştir.   

Bu raporun amacı, sadece mevcut yöntemleri listelemek değil, bu yöntemlerin altında yatan teorik zeminleri, deneysel sonuçları ve gelecekteki araştırma yönlerini sentezlemektir. Rapor, ajan mimarileri, istem mühendisliği (prompt engineering), öz-düşünüm (self-reflection), çoklu ajan sistemleri ve sektörel uygulamalar olmak üzere beş ana eksende yapılandırılmıştır.

2. Ajan Mimarilerinde Temel Paradigma Değişimi: Akıl Yürütme ve Eylem Entegrasyonu
Geleneksel LLM kullanımı, modelin içsel parametrik bilgisine dayanarak soruları yanıtlaması üzerine kuruluydu. Ancak, bu yaklaşım halüsinasyon (gerçek dışı bilgi üretme) ve güncel bilgiye erişememe gibi temel sorunları beraberinde getirmekteydi. Ajan tabanlı sistemlerin doğuşu, bu kısıtlamaları aşmak için modellerin dış araçlarla (API'ler, veritabanları, kod yorumlayıcılar) entegre edilmesiyle mümkün olmuştur.

2.1. ReAct: Akıl Yürütme ve Eylemin Sinerjisi
Ajan tabanlı YZ literatüründeki en temel taşlardan biri olan ReAct (Reasoning and Acting), dil modellerinin problem çözme yeteneklerini artırmak için akıl yürütme izleri (reasoning traces) ile göreve özgü eylemleri (actions) iç içe geçiren bir yöntem önermiştir. ReAct öncesinde, modeller ya sadece akıl yürütüyor (Chain-of-Thought - CoT) ya da sadece eylem gerçekleştiriyordu. ReAct, bu iki süreci tek bir döngüde birleştirmiştir.   

2.1.1. Çalışma Mekanizması
ReAct paradigması, modelin bir "Düşünce" (Thought), ardından bir "Eylem" (Action) ve sonrasında dış dünyadan gelen bir "Gözlem" (Observation) üretmesi prensibine dayanır.   

Düşünce: Ajan, mevcut durumu analiz eder ve ne yapması gerektiğini planlar (Örn: "Kullanıcının sorduğu yazarın doğum tarihini bulmam gerekiyor.").

Eylem: Ajan, dış bir kaynağa (Wikipedia API vb.) sorgu gönderir.

Gözlem: Dış kaynaktan gelen veri modele geri beslenir.

Bu döngüsel yapı, modelin kendi akıl yürütme sürecini dış dünyadan gelen kanıtlarla temellendirmesini sağlar. HotpotQA ve Fever gibi veri setlerinde yapılan deneyler, ReAct'in sadece CoT kullanan yöntemlere kıyasla halüsinasyon oranlarını ciddi ölçüde azalttığını ve hata yayılımını (error propagation) engellediğini göstermiştir. Örneğin, model yanlış bir varsayımda bulunsa bile, eylem sonucunda gelen gözlem bu varsayımı düzeltebilir.   

2.1.2. Kısıtlamalar ve Maliyet
ReAct'in başarısına rağmen, literatürdeki eleştiriler bu yöntemin verimsizliğine işaret etmektedir. Modelin her adımda durup dış dünyadan yanıt beklemesi ve her adım için tekrar tekrar LLM'e sorgu atılması, "Token" maliyetlerini ve işlem süresini artırmaktadır. Ayrıca, bağlam penceresinin (context window) sürekli olarak geçmiş düşünce ve gözlemlerle dolması, modelin dikkat mekanizmasını zorlayabilmektedir.   

2.2. ReWOO: Gözlemden Arındırılmış Akıl Yürütme
ReAct'in verimsizliklerine bir yanıt olarak geliştirilen ReWOO (Reasoning WithOut Observation), akıl yürütme sürecini dış gözlemlerden ayıran modüler bir paradigma sunmaktadır. Bu yaklaşım, ardışık ve duraklamalı bir süreç yerine, planlama ve yürütme aşamalarını birbirinden izole eder.   

2.2.1. Modüler Mimari: Planlayıcı, İşçi ve Çözücü
ReWOO, süreci üç ana bileşene ayırır:

Planlayıcı (Planner): Sorunu analiz eder ve dış araçlardan gelecek verilere bağımlı olmayan, öngörülebilir bir plan taslağı oluşturur. Bu plan, birbirine bağlı adımları içerir ancak bu aşamada hiçbir araç çalıştırılmaz.   

İşçi (Worker): Planlayıcının oluşturduğu talimatları alır ve ilgili araçları (API çağrıları vb.) çalıştırır. Kritik bir avantaj olarak, bu araç çağrıları paralel olarak yürütülebilir, bu da süreci büyük ölçüde hızlandırır.   

Çözücü (Solver): Başlangıçtaki soruyu, Planlayıcının taslağını ve İşçinin topladığı kanıtları sentezleyerek nihai yanıtı üretir.   

2.2.2. Performans ve Verimlilik Analizi
ReWOO, HotpotQA gibi çok adımlı akıl yürütme görevlerinde ReAct'e kıyasla 5 kat daha az token kullanarak benzer veya daha yüksek doğruluk oranlarına (%4 artış) ulaşmıştır. Bu bulgu, ajanların her adımda "düşünmesine" gerek olmadığını, iyi bir ön planlamanın daha efektif olduğunu göstermektedir. Ayrıca, ReWOO'nun modüler yapısı, planlama yeteneğinin devasa modellerden (Örn: GPT-3.5) daha küçük modellere (Örn: LLaMA-7B) damıtılmasını (distillation) mümkün kılarak, daha az kaynağa sahip ortamlarda ajan kullanımının önünü açmaktadır.   

2.3. Karşılaştırmalı Analiz: ReAct vs. ReWOO
Aşağıdaki tablo, bu iki temel paradigmanın teknik farklarını özetlemektedir:

Özellik	ReAct (Sinerjik Yaklaşım)	ReWOO (Ayrıklaştırılmış Yaklaşım)
Süreç Akışı	Düşünce → Eylem → Gözlem (Döngüsel)	Planla → Çalıştır → Çöz (Doğrusal/Paralel)
LLM Çağrı Sayısı	Adım sayısı kadar (Yüksek)	Genellikle 2-3 (Düşük)
Hata Yönetimi	Anlık düzeltme mümkün (Dinamik)	Plan hatası tüm süreci etkileyebilir (Statik)
Token Verimliliği	Düşük (Sürekli bağlam tekrarı)	
Yüksek (%80'e varan tasarruf) 

Uygulama Alanı	Bilinmeyenlerin çok olduğu, dinamik ortamlar	Yapısı belli, planlanabilir görevler
  
Bu karşılaştırma, literatürün "her şeye uyan tek model" yaklaşımından uzaklaşıp, görevin niteliğine göre mimari seçimi yapılması gerektiği yönündeki eğilimini doğrulamaktadır. ReWOO, yapılandırılmış veri çekme görevlerinde üstünken, ReAct belirsizlik içeren keşifsel görevlerde hala geçerliliğini korumaktadır.

3. İstem Mühendisliği ve Akıl Yürütme Stratejileri
Ajanların temelini oluşturan LLM'lerin performansını artırmak için sadece mimari değişiklikler değil, aynı zamanda istem (prompt) stratejilerinde de yenilikler gerekmektedir. Literatür, basit "adım adım düşün" (Zero-shot-CoT) komutlarının ötesine geçen teknikleri incelemektedir.

3.1. Plan-and-Solve (PS) Prompting
Standart Zero-shot-CoT yaklaşımı, özellikle aritmetik ve sembolik problemlerde üç temel hata türü sergilemektedir: hesaplama hataları (%7), adım atlama hataları (%12) ve anlamsal yanlış anlama (%27). Bu hataları minimize etmek için geliştirilen Plan-and-Solve (PS) Prompting, modele soruyu çözmeye başlamadan önce açık bir plan yapması talimatını verir.   

Genişletilmiş PS+ Prompting yöntemi ise daha spesifik talimatlar ekler: "İlgili değişkenleri çıkar" ve "ara sonuçları hesapla". Bu yöntem, MultiArith veri setinde %91.8 doğruluk oranına ulaşarak, 8-shot (8 örnekli) CoT ile rekabet edebilir düzeye gelmiştir. Bu durum, modelin "bilişsel yükünü" planlama ve yürütme aşamalarına bölmenin, işlem gücünü daha verimli kullanmasını sağladığını göstermektedir.   

3.2. Çok Örnekli Öğrenme Paradoksu (Many-Shot Paradox)
LLM'lerin bağlam pencerelerinin genişlemesi (1 milyon token ve üzeri), "In-Context Learning" (Bağlam İçi Öğrenme) için modele yüzlerce örnek verilmesi (Many-Shot Prompting) fikrini cazip hale getirmiştir. Ancak, kod çevirisi üzerine yapılan geniş çaplı bir ampirik çalışma (90.000 deneme), şaşırtıcı bir "Many-Shot Paradoksu" ortaya koymuştur.   

Araştırma bulgularına göre:

Statik benzerlik metrikleri (kodun yüzeysel benzerliği), örnek sayısı arttıkça artış göstermektedir.

Ancak, fonksiyonel doğruluk (kodun gerçekten çalışıp doğru sonucu vermesi), 5 ile 25 örnek arasında zirve yapmakta, 625 örneğe çıkıldığında ise düşüşe geçmektedir.   

Bu bulgu, literatürdeki "daha fazla veri her zaman iyidir" algısını sarsmaktadır. Kod çevirisi gibi katı mantıksal kısıtlamaları olan görevlerde, modelin dikkati aşırı sayıda örnekle dağılabilmekte veya model, örneklerin yüzeysel kalıplarını ezberleyip altta yatan mantığı göz ardı edebilmektedir. Bu nedenle, literatür artık örnek kalitesinin, niceliğinden çok daha kritik olduğunu vurgulamaktadır.

4. Öz-Düşünüm ve Kendi Kendini Düzeltme Mekanizmaları
Ajanların otonomisini artıran en önemli faktörlerden biri, hata yaptıklarında bunu fark edip düzeltebilme yetenekleridir. Literatür, bu alanda "İçsel" ve "Dışsal" geri bildirim mekanizmaları olmak üzere iki ana yol izlemektedir.

4.1. Reflexion: Sözel Pekiştirmeli Öğrenme
Geleneksel Pekiştirmeli Öğrenme (Reinforcement Learning - RL), model ağırlıklarının güncellenmesini gerektirir ki bu da LLM'ler için oldukça maliyetlidir. Reflexion çerçevesi, bu süreci ağırlık güncellemesi olmadan, sözel geri bildirim (verbal reinforcement) yoluyla gerçekleştirmeyi önerir.   

Reflexion ajanı bir görevde başarısız olduğunda, hatanın nedenini açıklayan metin tabanlı bir "yansıma" (reflection) üretir ve bunu epizodik hafızasında saklar. Bir sonraki denemede, bu hafıza kaydı bağlama eklenerek ajanın aynı hatayı tekrarlaması engellenir. HumanEval kodlama testlerinde, Reflexion kullanan GPT-4, %80 başarı oranını %91'e çıkarmıştır. Bu, ajanların deneyimden öğrenmesi için parametre güncellemenin şart olmadığını, hafıza yönetimi ve öz-eleştirinin yeterli olabileceğini kanıtlamaktadır.   

4.2. CRITIC: Araç Destekli Doğrulama
Modelin kendi çıktısını sadece kendi iç bilgisiyle doğrulaması (intrinsic self-correction), genellikle güvenilmezdir çünkü model halüsinasyonuna aşırı güven duyabilir. CRITIC çerçevesi, bu sorunu çözmek için ajanların tıpkı insanlar gibi dış araçları kullanarak kendi çıktılarını doğrulamasını sağlar.   

CRITIC süreci şöyledir:

Model bir yanıt üretir.

Yanıtın şüpheli kısımları için dış araçlarla (Google Arama, Python yorumlayıcısı) etkileşime geçer.

Araçlardan gelen kanıtlara dayanarak yanıtını revize eder.

Bu yöntem, toksik içerik üretimini %79.2 oranında azaltmış ve matematiksel akıl yürütme görevlerinde %7'lik bir iyileşme sağlamıştır. CRITIC çalışması, LLM'lerin "doğuştan" gelen bir doğrulama yeteneğine sahip olmadığını, bu yeteneğin ancak dış referanslarla kazanıldığını vurgulamaktadır.   

5. Kolektif Zeka: Çoklu Ajan Sistemleri (Multi-Agent Systems)
Tek bir ajanın kapasitesinin sınırlarına ulaşıldığında, literatür çözüm olarak çoklu ajan mimarilerine yönelmektedir. Bu sistemler, farklı uzmanlıklara sahip modellerin işbirliği yaparak, tekil modellerden daha üstün sonuçlar üretmesine dayanır.

5.1. Mixture-of-Agents (MoA): İşbirliğinin Gücü
Mixture-of-Agents (MoA), "Mixture-of-Experts" (Uzmanların Karışımı) kavramını model seviyesine taşıyan bir yaklaşımdır. MoA, katmanlı bir mimari kullanır; her katmanda birden fazla LLM (ajan) bulunur.   

Çalışma Prensibi: İlk katmandaki ajanlar (Teklif Verenler - Proposers) bağımsız yanıtlar üretir. Sonraki katmandaki ajanlar (Birleştiriciler - Aggregators), önceki katmanın tüm yanıtlarını girdi olarak alır ve bunları sentezleyerek daha iyi bir yanıt oluşturur.

İşbirlikçilik Fenomeni (Collaborativeness): Araştırmanın en çarpıcı bulgusu, LLM'lerin diğer modellerden gelen çıktıları gördüklerinde, bu çıktılar kendilerinden daha düşük kalitede olsa bile, kendi yanıtlarını iyileştirebilmeleridir.   

Sonuçlar: Sadece açık kaynaklı modellerin (Qwen, LLaMA-3, Mistral) kullanıldığı bir MoA sistemi, AlpacaEval 2.0 testinde %65.1 kazanma oranıyla, o dönemki en güçlü kapalı model olan GPT-4 Omni'yi (%57.5) geride bırakmıştır. Bu, açık kaynak ekosisteminin kolektif gücünün, tescilli dev modelleri geçebileceğini göstermesi açısından devrim niteliğindedir.   

5.2. CAMEL: Rol Yapma Yoluyla İletişim
CAMEL (Communicative Agents for "Mind" Exploration) çerçevesi, iki ajanın (örneğin bir "Kullanıcı" ve bir "Asistan") belirli roller üstlenerek (Role-Playing) bir görevi tamamlamak için otonom olarak sohbet etmesini sağlar.   

Inception Prompting: Ajanların rollerinden çıkmamaları ve göreve odaklanmaları için özel bir başlangıç istemi kullanılır.

Veri Üretimi: CAMEL, ajanların birbirleriyle konuşarak ürettikleri diyalogların, eğitim verisi olarak çok değerli olduğunu göstermiştir. Örneğin, "Yazılım Mühendisi" ve "Borsa Uzmanı" rollerindeki iki ajanın etkileşimi, borsa botu yazma konusunda insan müdahalesi olmadan zengin bir veri seti oluşturabilir.

6. Değerlendirme Paradigmaları: Ajanı Ajanla Yargılamak
Ajanların yetenekleri arttıkça, onları değerlendirmek de zorlaşmaktadır. Statik test setleri (benchmark) yetersiz kalmakta, insan değerlendirmesi ise ölçeklenememektedir.

6.1. Agent-as-a-Judge
Agent-as-a-Judge (Yargıç Olarak Ajan) çerçevesi, ajan sistemlerini değerlendirmek için yine ajanları kullanmayı önerir. Bu yaklaşım, sadece nihai sonucu değil, ajanın problemi çözerken izlediği süreci de değerlendirebilir.   

DevAI Benchmark: Bu yaklaşımı test etmek için, 55 gerçekçi yapay zeka geliştirme görevi ve 365 hiyerarşik gereksinimden oluşan DevAI seti oluşturulmuştur.

Güvenilirlik ve Maliyet: Agent-as-a-Judge yöntemi, insan değerlendiricilerle %90 oranında uyum göstermiş (önceki LLM-as-a-Judge yöntemlerinde bu oran %70 civarındaydı) ve insan değerlendirmesine göre %97 maliyet tasarrufu sağlamıştır. Bu, ajanların kendi kendilerini geliştirme döngüsünde (self-improvement loop) insan gözetimine olan ihtiyacı azaltacak kritik bir adımdır.   

7. Özelleşmiş Uygulamalar ve Teknik Derinleşme
Literatür taraması, genel amaçlı ajanların yanı sıra, belirli problemlere özgü geliştirilen yenilikçi mimarileri de ortaya koymaktadır.

7.1. Gerçek Zamanlı Video Çevirisi ve Token Ring Mimarisi
Çok dilli video konferans sistemlerinde üretken yapay zeka (GenAI) kullanımı, hesaplama maliyeti ve gecikme (latency) sorunları nedeniyle zordur. Katılımcı sayısı arttıkça işlem yükü karesel (O(N 
2
 )) olarak artar.

MDPI kaynaklı bir çalışma, bu sorunu çözmek için Token Ring (Jeton Halkası) mekanizmasını önermektedir.   

Mekanizma: Sistemde sadece o anda konuşan kişi (Aktif Konuşmacı) için çeviri boru hattı (pipeline) aktif edilir. Diğer katılımcılar "Pasif Dinleyici" modundadır. Bu sayede işlem karmaşıklığı doğrusal (O(N)) seviyeye indirilir.

Parçalı İşleme (Segmented Processing): Gecikmeyi yönetmek için konuşma küçük parçalara bölünür. Kullanıcı testleri, kullanıcıların akıcı bir oynatma deneyimi karşılığında, başlangıçta öngörülebilir bir gecikmeyi (initial buffering) kabul ettiklerini göstermiştir. Bu mimari, teorik yapay zeka modellerinin gerçek dünya mühendislik kısıtlamalarıyla nasıl uyumlu hale getirilebileceğine dair mükemmel bir örnektir.

7.2. Hata Tespiti için Doğal Dil Özetleme (Bug Localization)
Mikroservis mimarilerinde hatanın kaynağını bulmak (Bug Localization), kod ve hata raporu arasındaki anlamsal boşluk nedeniyle zordur. Natural Language Summarization çalışması, kaynak kodun ham halini kullanmak yerine, kod tabanını hiyerarşik doğal dil özetlerine dönüştürmeyi önerir.   

Yöntem: Kod tabanı, "Depo → Dizin → Dosya" şeklinde özetlenir. Ajan, hata raporunu bu özetlerle karşılaştırarak "NL-to-NL" (Doğal Dilden Doğal Dile) araması yapar.

Sonuç: Bu yöntem, ham kod üzerinde vektör araması yapan (RAG) yöntemlere kıyasla daha yüksek başarı (Pass@10: 0.82) sağlamıştır. Bu, kodun anlamsal temsili üzerinden akıl yürütmenin, doğrudan kod üzerinde işlem yapmaktan daha etkili olabileceğini göstermektedir.

7.3. ReFusion: Difüzyon Tabanlı Dil Modelleri
Geleneksel LLM'ler otoregresif (soldan sağa, kelime kelime) çalışır. Bu durum yavaştır. ReFusion, dil üretimi için Maskelenmiş Difüzyon Modellerini (Masked Diffusion Models) kullanır.   

Yenilik: ReFusion, üretimi token seviyesinden "Slot" (yuva/bölüm) seviyesine taşır. Bir "planla-ve-doldur" (plan-and-infill) süreci izler. Önce taslak bir plan çıkarılır (difüzyon ile), sonra bu planın içi paralel olarak doldurulur.

Performans: Bu yöntem, diğer difüzyon modellerine göre %34 performans artışı ve 18 kat hızlanma sağlamıştır. Bu, ajanların gelecekte otoregresif darboğazdan kurtulup çok daha hızlı düşünebileceğine işaret etmektedir.

7.4. Fizik Problemleri ve Biçimsel Akıl Yürütme: Lean4Physics
Ajanların matematiksel ve fiziksel akıl yürütme yetenekleri genellikle zayıftır. Lean4Physics çalışması, üniversite seviyesindeki fizik problemlerini çözmek için Lean4 teorem kanıtlayıcısını kullanan bir çerçeve sunar.   

Önemi: Doğal dilin belirsizliğinden kaçınmak için problemleri biçimsel (formal) bir dile dökmek ve matematiksel kesinlikle çözmek, ajanların bilimsel alanlardaki güvenilirliğini artırmaktadır. Ancak mevcut modellerin (Claude-Sonnet vb.) bu alandaki başarısı hala düşüktür (%16-%35), bu da alanın henüz emekleme aşamasında olduğunu göstermektedir.

8. Güvenlik ve Tehditler: Yapısal Zafiyetler
Ajanların karmaşık talimatları ve yapıları takip etme yeteneği, aynı zamanda bir güvenlik açığına dönüşmektedir.

8.1. BreakFun: Şema İstismarı ile Jailbreak
BreakFun çalışması, LLM'lerin yapılandırılmış verilere (JSON, YAML vb.) uyma eğilimini kötüye kullanan bir saldırı yöntemidir.   

Yöntem: Saldırgan, zararlı bir niyeti (örneğin bomba yapımı), masum görünen bir hikaye ve karmaşık bir "Truva Atı Şeması" (Trojan Schema) içine gizler. Model, şemanın yapısına uymaya çalışırken, güvenlik filtrelerini aşarak zararlı içeriği üretir.

Sonuç: Bu yöntem, önde gelen modellerde %89 ile %100 arasında değişen saldırı başarı oranlarına (ASR) ulaşmıştır.

Savunma: "Adversarial Prompt Deconstruction" (Çekişmeli İstem Çözümlemesi) adı verilen bir savunma mekanizması, istemdeki tüm yapısal öğeleri kaldırıp sadece düz metni analiz ederek bu saldırıyı %100'e yakın oranda engelleyebilmektedir. Bu durum, ajanların "bürokratik" itaatkarlığının (yapıya uyma zorunluluğu) nasıl manipüle edilebileceğini gözler önüne sermektedir.

9. Sentez ve Gelecek Görünümü
İncelenen literatür ışığında, Ajan Tabanlı Yapay Zeka alanında şu ana trendler ve çıkarımlar belirginleşmektedir:

Monolitik Yapıdan Modülerliğe Geçiş: ReWOO ve MoA çalışmaları, her şeyi yapan tek bir dev model yerine, özelleşmiş (Planlayıcı, İşçi, Doğrulayıcı) modüllerden oluşan sistemlerin daha verimli ve başarılı olduğunu kanıtlamaktadır. Gelecekte, "işletim sistemi" benzeri, farklı modelleri ve araçları yöneten üst katman ajan mimarileri standartlaşacaktır.

Akıl Yürütmenin Ayrıklaştırılması: ReAct ile başlayan iç içe geçmiş döngüler, maliyet ve hız baskısı nedeniyle yerini ReWOO ve ReFusion gibi ayrıklaştırılmış (decoupled) ve paralel işlenebilir süreçlere bırakmaktadır. Düşünme ve eyleme geçme süreçlerinin zaman ekseninde ayrılması, ajanların daha stratejik ve daha az tepkisel (reactive) olmasını sağlamaktadır.

Kolektif ve Açık Kaynak Zekası: MoA çalışması, açık kaynak modellerin işbirliği yaparak kapalı kaynak devlerini geçebileceğini göstermiştir. Bu, yapay zeka demokratikleşmesi açısından kritik bir bulgudur.

Güvenlik ve Doğrulama Zorunluluğu: CRITIC ve BreakFun çalışmaları, modellerin kendi kendilerine güvenilemeyeceğini, dış doğrulama araçlarının ve güvenlik katmanlarının "isteğe bağlı" değil, "zorunlu" bileşenler olduğunu ortaya koymaktadır.

Veri Odaklı Değerlendirme: Agent-as-a-Judge ve DevAI gibi çalışmalar, ajanları değerlendirmenin tek yolunun yine ajanlar olduğunu, insan değerlendirmesinin artık bir darboğaz haline geldiğini göstermektedir.

Sonuç olarak, Yapay Zeka, pasif bir bilgi kaynağından, dünyayı algılayan, planlayan, diğer ajanlarla işbirliği yapan ve kendi hatalarından ders çıkaran aktif bir aktöre dönüşmektedir. Bu dönüşüm, yazılım mühendisliğinden (bug localization) medya üretimine (video translation) kadar her sektörü kökten değiştirme potansiyeline sahiptir.

Raporu Hazırlayan: Tarih: Aralık 2025 Kaynaklar:.   


openreview.net
ReAct: Synergizing Reasoning and Acting in Language Models ...
Yeni pencerede açılır

semanticscholar.org
ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models - Semantic Scholar
Yeni pencerede açılır

proceedings.neurips.cc
Reflexion: language agents with verbal reinforcement learning
Yeni pencerede açılır

arxiv.org
arXiv:2406.04692v1 [cs.CL] 7 Jun 2024 - Salvador Vilalta
Yeni pencerede açılır

arxiv.org
[2305.18323] ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models - arXiv
Yeni pencerede açılır

ai.plainenglish.io
Reasoning Without Observation (ReWOO) with Gemini 2.0 | by Amir imani
Yeni pencerede açılır

medium.com
On short of “ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models” | by Minh Le Duc | Medium
Yeni pencerede açılır

openreview.net
DECOUPLING REASONING FROM OBSERVATIONS FOR EFFICIENT AUGMENTED LANGUAGE MODELS | OpenReview
Yeni pencerede açılır

ibm.com
What is ReWOO? - IBM
Yeni pencerede açılır

arxiv.org
Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought ...
Yeni pencerede açılır

blog.langchain.com
[2305.04091] Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models - LangChain Blog
Yeni pencerede açılır

arxiv.org
When Many-Shot Prompting Fails: An Empirical Study of LLM Code Translation - arXiv
Yeni pencerede açılır

arxiv.org
When Many-Shot Prompting Fails: An Empirical Study of LLM Code Translation - arXiv
Yeni pencerede açılır

arxiv.org
Confidence Matters: Revisiting Intrinsic Self-Correction Capabilities of Large Language Models - arXiv
Yeni pencerede açılır

aclanthology.org
CRITICTOOL: Evaluating Self-Critique Capabilities of Large Language Models in Tool-Calling Error Scenarios - ACL Anthology
Yeni pencerede açılır

arxiv.org
CRITIC: Large Language Models Can Self-Correct with Tool ...
Yeni pencerede açılır

marktechpost.com
Mixture-of-Agents (MoA): A Breakthrough in LLM Performance - MarkTechPost
Yeni pencerede açılır

proceedings.neurips.cc
CAMEL: Communicative Agents for "Mind" Exploration of Large ...
Yeni pencerede açılır

semanticscholar.org
[PDF] Agent-as-a-Judge: Evaluate Agents with Agents - Semantic Scholar
Yeni pencerede açılır

summarizepaper.com
AI-Powered Paper Summarization about the arXiv paper 2410.10934v1
Yeni pencerede açılır

openreview.net
Agent-as-a-Judge: Evaluate Agents with Agents - OpenReview
Yeni pencerede açılır

mdpi.com
Generative AI for Video Translation: A Scalable Architecture for Multilingual Video Conferencing - MDPI
Yeni pencerede açılır

themoonlight.io
[論文評述] Generative AI for Video Translation: A Scalable Architecture for Multilingual Video Conferencing - Moonlight
Yeni pencerede açılır

arxiv.org
[2512.05908] Natural Language Summarization Enables Multi-Repository Bug Localization by LLMs in Microservice Architectures - arXiv
Yeni pencerede açılır

arxiv.org
[2512.13586] ReFusion: A Diffusion Large Language Model with Parallel Autoregressive Decoding - arXiv
Yeni pencerede açılır

arxiv.org
[2510.26094] Lean4Physics: Comprehensive Reasoning Framework for College-level Physics in Lean4 - arXiv
Yeni pencerede açılır

arxiv.org
[2510.17904] BreakFun: Jailbreaking LLMs via Schema Exploitation - arXiv