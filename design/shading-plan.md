# Návrh řízení stínění a výběr Zigbee hardwaru

Stav k 16. 9. 2026: návrh, nikoli implementovaná nebo aktivovaná automatizace. PDF objednávky bylo přečteno; potvrzuje pět venkovních rolet FINALM a motorové místní ovládání Somfy ILMO WT. Přesné varianty motorů a kabeláž u vypínačů ještě nejsou doložené. Žádný commit ani deploy. Existující změny topení tento dokument nemění.

## Co potvrzuje objednávka

Zdroj: uživatelem dodaná „631730 Smlouva.pdf“, zejména strana 4, **CENOVÝ ROZPOČET – venkovní rolety FINALM**, oddíl **Motorové místní ovládání Somfy ILMO WT**. Z přílohy přebíráme pouze technické parametry potřebné pro návrh.

| Pozice | Rozměr rolety (š × v, mm) | Počet | Pohon podle kategorie rozpočtu |
| --- | --- | --- | --- |
| 1 | 3449 × 2093 | 1 | jeden pohon do 10,5 m², přiřazení podle velikosti je inference |
| 2 | 1450 × 1220 | 1 | čtyři menší pohony do 4 m² |
| 3 | 1452 × 1220 | 1 | viz menší pohony |
| 4 | 1448 × 1220 | 1 | viz menší pohony |
| 5 | 1448 × 1220 | 1 | viz menší pohony |

Každá roleta má samostatné místní ovládání, rozpočet uvádí zapojení pěti cizích tlačítek. Obsahuje také čtyři integrované sítě a jednu plisovanou síť; nic nedokládá jejich motorizaci. Tyto sítě tedy nepřidáváme jako ovládané cover entity. Názvy místností a orientace nejsou uvedené. Velkou pozici 1 nepovažujeme automaticky za terasové dveře, dokud to uživatel nepotvrdí.

Jde o navíjecí rolety: náklon lamel nepotřebujeme. WT je drátové rozhraní; označení Somfy zde neznamená nutnost io/RTS hubu. Věta o chybějícím centrálním ovládání popisuje dodanou variantu, nikoli automatický zákaz dodatečného vhodného řadiče. Pro potvrzení je potřeba konkrétní motor a zapojení. [Somfy – drátová technologie WT](https://www.somfy.cz/produkty/venkovni-stineni/venkovni-rolety/jak-vybrat-motor-pro-rolety)

## Zvolený hardware a rozsah review

Uživatel 16. 9. 2026 potvrdil nákup **5× SONOFF Fusion Series Orb-ZBRBS, MINI-ZBRBS-E**. Návrh nyní cílí na tento kompletní nástěnný roletový vypínač, jeden na každý motor. Dřívější doporučení pilotu Shelly je nahrazené tímto rozhodnutím. Nákup není potvrzení zapojení, kalibrace ani kompatibility konkrétního motoru.

K review je připraven tento návrh a datový inventář `design/shading-inventory.yaml`. Automatizace rolet ani jejich testy zatím implementované nejsou. Existující implementace topení a jeho lab jsou samostatné změny. Review návrhu neaktivuje zařízení.

Z uživatelova popisu známe sestavy: místo 1 = roleta + dvojvypínač světel + jednovypínač světel; místo 2 = roleta + dvojvypínač světel; další tři místa = pouze roleta. Není potvrzené přiřazení těchto míst k pozicím objednávky. Nákup světelných vypínačů ani rámečků potvrzený není a není součástí řízení rolet.

Limit SONOFF 1 A nelze ověřit z plochy okna. Velká roleta má přibližně 7,22 m² a jinou výkonovou kategorii. Historický technický list ILMO 50 TH WT například uvádí variantu 30/17 s 1,1 A; to dokládá, proč nesmíme proud odhadnout pouze z názvu ILMO. Nejde o identifikaci objednaného motoru ani současný katalogový výběr. [Technický list Somfy](https://service.somfy.com/downloads/fr_v5/datasheetilmo_50_th_wt_range1r0.pdf)

**ubisys J1 pro tuto zakázku vyřazuji z doporučení:** jeho dokumentace popisuje polovodičové spínání. Pokyny Somfy pro WT, výslovně včetně Ilmo 40/50 WT, použití polovodičových relé vylučují. Současně vyžadují blokování směrů a uvádějí orientační pauzu změny směru 500 ms. Tyto podmínky musí splnit samotný řadič i při místním ovládání, nikoli až automatizace HA. [Somfy – pravidla řízení WT, strana 45](https://downloads.somfy.de/frontend/getcatalog.do?catalogId=354615&catalogVersion=11&startpage=45), [ubisys – způsob spínání](https://www.ubisys.de/downloads/ubisys-j1-technical-reference.pdf)

Od dodavatele/elektrikáře potřebujeme: přesná označení a jmenovité proudy obou výkonových kategorií, požadavky na řadič a pauzu při reverzaci, typ objednaných tlačítek, dostupnost L/N a motorových vodičů v místě modulu, prostor v krabicích a provedení jištění. Pilot musí ověřit kalibraci s elektronickými koncovými polohami ILMO a chování při překážce/přimrznutí. Ochrana uvnitř motoru neznamená, že HA dostane samostatnou zprávu o překážce.

## Rozhodnutí, která lze udělat už teď

Navrhuji samostatný řadič stínění se společným rozhraním HA `cover`. Hardware musí sám zvládat motor, místní ovládání, koncové polohy a vzájemné blokování směrů. HA vybírá požadovanou polohu; negeneruje přesné časování motorových relé. Rozhraní může volitelně podporovat náklon lamel. Tím zůstane logika použitelná pro různé moduly. [Rozhraní cover v HA](https://www.home-assistant.io/integrations/cover/)

Konfigurace v repozitáři používá Zigbee2MQTT, adaptér ember a kanál 15. Nejde o ověření živé sítě. V domě již existuje `cover.garage_door`: skupiny stínění proto budou mít explicitní seznam členů, nikdy automaticky všechny entity domény `cover`.

## Rozhraní zakoupeného MINI-ZBRBS-E

Výrobce potvrzuje Zigbee router, nulový vodič, motor nejvýše 1 A a nejvýše dvě minuty nepřetržitého chodu v jednom směru. Kompletní přístroj má rozměry 86 × 86 × 34 mm; nejde o rozměry samotného modulu MINI-ZBRBS. [Výrobce](https://sonoff.tech/products/sonoff-fusion-series-orb-zbrbs-zigbee-smart-roller-shutter-wall-switch)

Také manuál varianty **-E** výslovně požaduje předřazené jištění 1 A. Provedení s elektrikářem ověřit před připojením; běžný světelný jistič nepovažujeme automaticky za splnění tohoto požadavku. Kalibrace zahrnuje skutečné pohyby motoru a zůstává řízeným úkonem při zprovoznění. [Manuál MINI-ZBRBS-E](https://support.sonoff.tech/mini-zbrbs-e-usermanual/)

Jako výchozí kontrakt použít dokumentaci Z2M pro MINI-ZBRBS; na zakoupeném -E ověřit skutečnou identifikaci a exposes. Zapsat verzi Z2M, firmware a mapování dostupných entit. Dokumentace uvádí OPEN/CLOSE/STOP, position, moving a stav/akce kalibrace. Neuvádí wattmetr, náklon ani samostatnou událost stisku fyzického tlačítka; na těch návrh nesmí záviset. [Zigbee2MQTT](https://www.zigbee2mqtt.io/devices/MINI-ZBRBS.html)

### Ruční zásah je hlavní bod pilotu

Ruční příkazy z navrženého panelu HA procházejí vlastním skriptem, který před pohybem nastaví ruční prioritu. Příkaz z jiné aplikace nebo fyzického tlačítka takto označený být nemusí. HA context sám neurčuje původ fyzického Zigbee pohybu.

Pohyb bez odpovídajícího vlastního příkazu lze zpracovat jako nevyžádaný pohyb a pozastavit automatiku; není to důkaz stisku tlačítka. Opožděný či opakovaný report vlastního pohybu nesmí vytvářet falešný ruční zásah. Předčasný stop nebo opačný směr během automatické jízdy má zrušit čekající cíle a pozastavit komfortní automatiku, ne vyvolat pokus o dokončení původního cíle. Přesnou korelaci a časová okna nastavit až podle záznamu pilotu.

Pokud nelze ruční přerušení dostatečně rozpoznat, na dané roletě nepovolit automatický režim; observe a místní ovládání zůstávají použitelné. Simulátor musí umět běh bez události tlačítka. Nesmí vytvářet pohodlnější rozhraní, než má hardware.

### Požadovaná versus hlášená poloha

Použít jednotnou konvenci HA: 0 % zavřeno, 100 % otevřeno, ověřenou na pilotu. Prověřit volbu Z2M `cover_position_tilt_disable_report: true`, aby samotný požadavek nebyl vydáván za hlášení dosažené polohy. Ani hlášení řadiče není nezávislý snímač polohy nebo průchodu. Nedosažení cíle zaznamenat jako závadu a blokovat další komfortní pokusy; bez automatické rekalibrace a nekonečných retry.

## Zigbee síť

Trvalé napájení ještě neznamená router; tu funkci je nutné ověřit pro konkrétní model a firmware. Router musí být členem stávající sítě, nikoli druhého hubu. Po spárování ověřit typ Router, dosažitelnost a reálné doručování zpráv okolních čidel. Samotná hodnota LQI není důkaz přínosu. [Typy Zigbee zařízení](https://www.zigbee2mqtt.io/advanced/zigbee/01_zigbee_network.html)

Pro rozložení sítě preferuji vhodné přístupné vnitřní krabice poblíž jednotlivých oken. Moduly soustředěné v kovovém rozvaděči nebo schované v kovových roletových boxech nemusí pomoci pokojům tolik. Umístění a provedení musí respektovat elektrické i teplotní podmínky výrobce. Routery mají být trvale napájené i při vypnutém motoru.

Nejdřív přidat jeden kus a sledovat síť několik dní, potom rozšiřovat. Přidáním routeru není zaručeno přepojení stávajících bateriových zařízení; připojení přes vybraný router není trvalé připnutí trasy. [Párování v Z2M](https://www.zigbee2mqtt.io/guide/usage/pairing_devices.html)

## Rozhodovací logika

Každé okno má vlastní profil a stav. Více oken v jedné místnosti může mít jinou orientaci a jinou roli; zejména terasové dveře se nesmějí chovat jako běžné okno.

1. **Povolení a připravenost:** bez přiděleného hardwaru a potvrzené kalibrace nevydávat automatické pohybové příkazy. Režimy `disabled`, `observe`, `automatic`. Disabled vypne řadič automatiky; observe pouze vypočítává návrh a důvod. Ani jeden režim neposílá automatické příkazy motoru, včetně automatického stop. Explicitní ruční ovládání je samostatné. Ochrany HA za pohybu jsou aktivní až v automatic; místní ochrany pohonu platí nezávisle. Kalibraci nespouštět automaticky při restartu.
2. **Ochrany:** porucha/překážka znamená stop a blokaci, bez opakovaného zkoušení. Pro vítr/mráz vyžaduje každé stínění vlastní pravidla výrobce. Není univerzální pravidlo „při větru vše vytáhnout“. Konflikt bezpečnostních požadavků má vést k blokaci a hlášení podle předem schváleného profilu, ne k hádání.
3. **Průchod:** otevřené nebo neznámé terasové dveře blokují automatické zavírání. Při otevření během automatického zavírání poslat stop; případné povytažení až podle ověřeného profilu. Po zavření dveří neprovést odložený starý příkaz, ale přepočítat aktuální situaci. Samotný kontakt nepozná člověka venku za zavřenými dveřmi: samostatný režim „terasa používána“ musí držet průchod volný, dokud ho někdo neuvolní.
4. **Ruční zásah:** tlačítko nebo explicitní ruční příkaz v HA přeruší komfortní automatiku a nastaví dočasnou prioritu uživatele. Návrh počátečního nastavení je dvě hodiny, plus volba „do zrušení“. Čas uložení musí přežít restart. Automatické stavové reporty nezaměňovat za ruční zásah.
5. **Soukromí a spánek:** večerní poloha podle místnosti a času/soumraku, ranní otevření nejdřív od stanoveného času. Režim spánku chrání ložnici před otevřením při východu slunce. Po ručním zastavení ho další periodický přepočet nesmí hned přebít.
6. **Tepelné stínění:** reagovat na slunce na konkrétní fasádě, teplotu místnosti a dostupné měření oslunění. Při přehřívání přistínit; pokud místnost potřebuje teplo a svítí slunce, dovolit sluneční zisky, pokud nemá přednost soukromí. Nevázat rozhodnutí na samotný stav kotle: může topit kvůli jiné místnosti. Při chybějícím čidle vynechat tepelnou optimalizaci, neoznačit chybu za chlad nebo noc.
7. **Klidový režim:** dočasný mrak nebo malá změna teploty nemá vyvolávat pohyb. Počáteční návrh k ladění: vstupní podmínka stabilní pět minut, oddělené prahy vstupu/výstupu, nejméně 15 minut mezi komfortními pohyby a změna cíle alespoň o 10 procentních bodů. Tyto prodlevy neplatí pro stop, ochranu průchodu a ruční příkaz. Teplotní a větrné prahy doplníme podle domu a výrobce.

Místní ovládání musí fungovat i bez HA/MQTT. To současně znamená, že HA nedokáže spolehlivě zakázat přímo připojené tlačítko při výpadku komunikace. Kritický zákaz pohybu nebo ochrana před větrem musí být proveditelné lokálně v pohonu/řadiči; bezdrátový dveřní kontakt a HA nejsou samy o sobě hardwarová bezpečnostní funkce.

## Návrh konfigurace jako kód

Navržené součásti: `shading_policy` pro rozhodování, `shading_control` pro odesílání/ověření a `shading_diagnostics` pro stav a důvody. Profily oken udržovat v jednom explicitním seznamu, ne v několika rozcházejících se automatizacích. Počet souborů přizpůsobit skutečné velikosti, bez budování obecného frameworku před prvním oknem.

Příklad datového profilu, **nejde o HA package ani hotový kód**:

```yaml
id: shutter_01
commissioned: false
mode: observe
cover_entity: null
kind: roller_shutter        # doloženo objednávkou
facade_azimuth_deg: null
room_temperature_entity: null
opening_contact_entity: null
protects_passage: null
capabilities:
  position: false
  tilt: false
  movement_feedback: false
  power_feedback: false
weather_profile: null
```

Statická konfigurace, mapování entit, orientace a prahy patří do Gitu. Běžný uživatelský stav (spánek, ruční priorita, režim terasy) do obnovovaných HA helperů. Jednorázové párování a kalibrace zůstávají úkony při zprovoznění; zvolená nastavení a firmware se zdokumentují. Nepřepisovat ručně interní registry `.storage`.

V aplikaci vystavit ovládání, režim a stručný důvod, například „pozastaveno ručně do 17:30“ nebo „blokováno: terasa“. V diagnostice oddělit požadovanou a hlášenou polohu. Odeslaných 50 % neznamená dosažených 50 %; některé reporty mohou být odhadované. Nepřítomnou podporu tilt neinzerovat.

Každá roleta dostane vlastní zpracování příkazů: poslední komfortní požadavek nahrazuje starší, stop má přednost a ruší čekající pohyby. Žádná dlouhá fronta historických cílů. Po restartu/reconnectu načíst stav a znovu vyhodnotit; nepřehrávat příkazy uložené v MQTT jako retained. Nepotvrzený pohyb znamená poruchu, ne nekonečné retry. Čas pohybu a toleranci stanovit podle kalibrace a manuálu.

V Recorderu doplnit konkrétní entity stínění a důvodů: konfigurace domu dnes doménu cover nezahrnuje. Sledovat počet pohybů, dobu chodu, chyby dosažení polohy a četnost ručních zásahů. To pomůže vyhodnotit, zda automatika uživateli vyhovuje.

## Testy před zapojením

Rozšířit existující lab o pět simulovaných MQTT cover zařízení bez tilt, s konečnou rychlostí, nezávislým reportem pohybu, simulací místního ovládání bez samostatné události tlačítka a poruchami. V observe režimu musí test zachytit nulu odeslaných motorových příkazů. Zkoušet skutečné YAML automatizace v HA.

Povinné scénáře: neaktivované okno; otevřené/unknown terasové dveře; člověk venku při zavřených dveřích a aktivním režimu terasy; ruční změna během jízdy; zachování ruční priority po restartu; krátký mrak bez pohybu; stabilní přehřátí pouze na osluněné fasádě; chybějící/stará teplota; chybějící údaj větru; konflikt ochran; požadovaný cíl bez skutečného pohybu; opožděné reporty; restart uprostřed pohybu; nedostupný broker; fyzické tlačítko bez HA; žádný automatický příkaz garážovým vratům. Poslední hardwarové scénáře ověřit i na pilotním modulu, simulátor je nenahradí.

Po potvrzení přesných motorů doplnit umístění, orientace a profily; následně implementovat první okno, nejdříve v labu a observe režimu. Tento dokument zatím žádnou konfiguraci HA neaktivuje a žádný test stínění ještě není implementovaný.

## Zpřesnění scénářů pro tuto objednávku

V první implementaci připravit pět samostatných rolet bez lamelového režimu. Každá dostane vlastní změřenou dobu jízdy; velká roleta nesdílí časování s malými. Procenta nejprve kontrolovat proti skutečné poloze. Částečné roztažení větracích štěrbin lze přidat jako později změřenou oblíbenou polohu, nikoli předpokládat univerzální procento.

Pilotní automatika má nejprve řešit ruční prioritu, ráno/večer a ochranu případného průchodu. Tepelné stínění přidat po přiřazení fasád a oken. Automatický pohyb při větru neurčovat bez údajů dodavatele pro konkrétní rolety, zvlášť nadrozměrnou pozici 1. Při detekované poruše nebo nedosažení cíle neposílat krátké série nahoru/dolů; neprovádět automatický reset pohonu. Zamezit automatice, která by mohla omylem napodobit servisní/programovací sekvence WT.
