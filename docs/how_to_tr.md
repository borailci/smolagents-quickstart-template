# Bu Projeyi Kullanma - Öğrenci Rehberi

Bu rehber, Smolagents şablonunda yapabileceğiniz her şeyi adım adım açıklıyor - temel kullanımdan kendi agent'larınızı ve araçlarınızı oluşturmaya kadar.

## Projede Neler Var

**Mevcut Kurulum (Tek Agent):**
- `ExampleToolCallingAgent` - Dosya sistemi araçları ve bir şaka API aracı ile donatılmış bir agent
- Agent ile konuşmak için Gradio sohbet arayüzü
- Örnek çalışma alanı ile belgeler ve kod dosyaları
- Dosya yönetimi araçları (oku, yaz, ara, dizinleri listele)

**İsteğe Bağlı Çoklu-Agent Kurulumu:**
- `ExampleManagerAgent` - Diğer agent'ları koordine eder
- Agent'lar arasında görevleri nasıl devrettiğini gösterir

## Proje Yapısı

```
smolagents-quickstart-template/
├── agents/
│   ├── example_tool_calling_agent.py    # Araçlarla çalışan agent
│   ├── example_manager_agent.py         # Yönetici agent (isteğe bağlı)
│   └── base_agent.py                    # Temel sınıflar
├── toolkits/
│   ├── example_joke_toolkit.py          # Şaka API aracı
│   └── filesystem_toolkit.py            # Dosya işlemleri
├── data/agent_workspace/                # Agent'ın dosya çalışma alanı
│   ├── example_docs/alan_turing.md     # Örnek belge
│   └── example_codes/car.c             # Örnek kod dosyası
├── ui/gradio_agent_ui.py               # Sohbet arayüzü
├── main.py                             # Uygulama giriş noktası
└── run.sh                              # Kolaylık betiği
```

## Agent'a Ne Sorabilirsiniz

Agent'ınız çalıştığında şu örnekleri deneyin:

### Dosya İşlemleri
- "Çalışma alanındaki dosyaları listele"
- "Alan Turing belgesini oku"
- ".c dosyalarını ara"
- "hello.py adında basit bir Python programı oluştur"
- "Çalışma alanı yapısını ağaç şeklinde göster"
- "groceries.txt dosyasına bir alışveriş listesi yaz"

### Eğlenceli Etkileşimler
- "Bana bir şaka anlat"
- "Bana bir şaka anlat ve dosyaya kaydet"
- "car.c dosyasını oku ve ne yaptığını açıkla"

### Karmaşık Görevler
- "Çalışma alanındaki tüm dosyaları bul, Alan Turing belgesini oku ve bir özet dosyası oluştur"
- "Basit bir hesap makinesi uygulayan bir Python dosyası oluştur"

## Öğrenme Alıştırmaları

### Alıştırma 1: Yeni Bir Araç Ekle

`toolkits/` içinde basit bir hesap makinesi aracı oluşturun:

1. `toolkits/calculator_toolkit.py` adında yeni bir dosya oluşturun:

```python
from smolagents import tool
from typing import List

@tool
def calculate(expression: str) -> float:
    """
    Matematiksel ifadeyi güvenli şekilde değerlendirir.
    
    Args:
        expression (str): "2 + 3 * 4" gibi matematiksel ifade
        
    Returns:
        float: Hesaplama sonucu
    """
    try:
        # Temel matematik için eval'i güvenli kullan
        allowed_chars = set('0123456789+-*/.() ')
        if all(c in allowed_chars for c in expression):
            return eval(expression)
        else:
            return "Hata: İfadede geçersiz karakterler var"
    except Exception as e:
        return f"Hata: {str(e)}"

class CalculatorToolkit:
    @staticmethod
    def get_tools() -> List:
        return [calculate]
```

2. Bunu `main.py` içinde agent'ınıza ekleyin:

```python
from toolkits.calculator_toolkit import CalculatorToolkit

# main() fonksiyonunda:
calc_tools = CalculatorToolkit.get_tools()
tool_calling_agent = ExampleToolCallingAgent(tools=joke_tools + filesystem_tools + calc_tools)
```

3. Şimdi agent'ınıza sorun: "15 * 7 + 23 hesapla"

### Alıştırma 2: Agent İstemlerini Değiştir

1. `prompts/prompts.py` dosyasını açın
2. `EXAMPLE_TOOL_CALLING_AGENT` istemini değiştirin:

```python
EXAMPLE_TOOL_CALLING_AGENT = """
Dosya yönetimi ve hesap makinesi araçlarına erişimi olan yardımcı bir assistantsınız. 
Kullanıcı dostusunuz ve şeyleri açık şekilde açıklarsınız. Hesap yaparken çalışmanızı gösterin.
Her zaman teşvik edici ve eğitici yanıtlar verin.
"""
```

3. Agent'ı yeniden başlatın ve kişiliğinin nasıl değiştiğini görün!

### Alıştırma 3: Çalışma Alanına Dosyalar Ekleyin

1. `data/agent_workspace/example_docs/` içinde yeni bir dosya oluşturun:

```bash
echo "# Proje Fikirlerim

1. Hava durumu uygulaması oluştur
2. Görev yöneticisi oluştur
3. Basit bir oyun yap

## Notlar
- Backend için Python kullan
- Flask veya FastAPI'yi düşün
" > data/agent_workspace/example_docs/proje_fikirlerim.md
```

2. Agent'a sorun: "Proje fikirleri dosyamı oku ve hava durumu uygulamasını planlamama yardım et"

### Alıştırma 4: Yeni Bir Agent Oluştur

1. `agents/example_tool_calling_agent.py` dosyasını `agents/ozel_agentim.py` olarak kopyalayın
2. İsim ve açıklamayı değiştirin:

```python
class OzelAgentim(BaseAgent):
    def __init__(self, tools: List[Tool]):
        super().__init__()

        self.agent = ToolCallingAgent(
            name="ozel_agentim",
            description="Kod yardımı konusunda uzmanlaşmış özel bir agent.",
            tools=tools,
            model=LiteLLMModel(model_id=LITELLM_MODEL_ID, api_key=LITELLM_API_KEY),
            instructions="Programlamayı öğrenmelerine yardımcı olan bir kod mentorusun. Açık açıklamalar ve örnekler ver."
        )
```

3. Bunu `main.py` içinde orijinal agent yerine kullanın

## Çoklu-Agent Modunu Etkinleştir

Agent'ların birlikte çalıştığını görmek ister misiniz? İşte nasıl:

1. `main.py` dosyasını açın
2. Bu satırları uncomment edin:

```python
# Diğer agent'ları yöneten bir yönetici agent <-- çoklu-agent orkestrasyonu için uncomment edin
manager_agent: BaseAgent = ExampleManagerAgent(
    tools=[], managed_agents=[tool_calling_agent.agent]
)
```

3. UI satırını değiştirin:

```python
ui = GradioAgentUI(agent=manager_agent)  # tool_calling_agent'dan manager_agent'a değiştirin
```

4. Uygulamayı yeniden başlatın

Şimdi sorun: "İşçi agent'ına Alan Turing dosyasını okut ve bir özet oluştur"

Yönetici görevi işçi agent'a devredecek!

## Gelişmiş Alıştırmalar

### Web Arama Aracı Oluştur

İnternette arama yapan bir araç ekleyin:

```python
import requests
from smolagents import tool

@tool
def web_search(query: str) -> str:
    """
    DuckDuckGo'dan bilgi arar (basit uygulama).
    
    Args:
        query (str): Ne aranacak
        
    Returns:
        str: Arama sonuçları
    """
    # Bu basitleştirilmiş bir örnek - pratikte uygun bir API kullanın
    return f"{query} için simüle edilmiş arama sonuçları"
```

### Not Tutma Agent'ı Oluştur

Çalışma alanında notları ve belgeleri organize etmeye odaklanmış bir agent oluşturun.

### Kod İnceleme Agent'ı Oluştur

Kod dosyalarını okuyup geri bildirim ve öneriler veren bir agent oluşturun.

## Öğrenciler İçin İpuçları

1. **Küçük başlayın**: Önce basit araçlar ekleyin, sonra karmaşıklığı artırın
2. **Kodu okuyun**: Mevcut agent'larda ve araçlarda kalıpları anlayın
3. **Deneyin**: Farklı istemlerin agent davranışını nasıl değiştirdiğini görün
4. **Çalışma alanını kullanın**: Agent dosyalar oluşturabilir ve değiştirebilir - projeler için kullanın!
5. **Araçları birleştirin**: Agent'a karmaşık görevler için birden fazla aracı birlikte kullanmasını sorun

## Yaygın Sorunların Sorun Giderme

- **Agent araçları kullanmıyor**: Araçların `main.py` içinde agent'a doğru eklendiğinden emin olun
- **İçe aktarma hataları**: Yeni sınıflarınızı doğru şekilde içe aktardığınızdan emin olun
- **Agent yanlış yanıtlar veriyor**: `prompts/prompts.py` içinde istemi ayarlamayı deneyin
- **Dosya işlemleri başarısız oluyor**: `AGENT_WORKSPACE_PATH` değerinin `.env` içinde doğru ayarlandığından emin olun

## Sonraki Adımlar

- Yukarıdaki tüm alıştırmaları deneyin
- Kendi benzersiz araçlarınızı oluşturun
- Farklı modellerin kişiliklerini deneyin
- Belirli bir görev için çoklu-agent sistemi oluşturun
- Yaratımlarınızı diğer öğrencilerle paylaşın!
