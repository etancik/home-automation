# Rolety — podklady k review

Aktualizace 16. 9. 2026. Zvolený hardware: 5× SONOFF Fusion Orb-ZBRBS MINI-ZBRBS-E, nákup potvrzený uživatelem. Bez commitu, push a deploye.

## Co je připravené

| Oblast | Skutečný stav |
| --- | --- |
| Topení | Implementované změny v pěti HA packages, testovací prostředí a testy v lokální větvi `test/heating-lab`; 30 staged souborů. V této aktualizaci nezměněno. |
| Rolety | Návrh a plánovací YAML inventář v `design/`; soubory nejsou načítané do HA ani labu. |
| Testy rolet | Scénáře navržené, implementace a spuštění teprve před námi. |
| Zakoupené přístroje | Ještě není ověřené párování, firmware, motory, montáž ani kalibrace. |

Repozitář: `work/home-automation`, větev `test/heating-lab`. Podrobný návrh: `design/shading-plan.md`; inventář: `design/shading-inventory.yaml`. Kopie pro čtení jsou vedle tohoto dokumentu jako `rolety-navrh.md` a `rolety-inventar.yaml`.

## Návrh chování k posouzení

| Situace | Navržené chování |
| --- | --- |
| Nezprovozněná roleta | Žádný automatický pohyb; počáteční režim observe. |
| Observe | Vypočítat cíl a důvod, neposlat žádný automatický příkaz. Ruční ovládání zůstává samostatné. |
| Ruční ovládání | Pozastavit komfortní automatiku na 2 hodiny, případně do ručního zrušení. Přežije restart. Rozpoznání fyzického tlačítka musí ověřit pilot. |
| Večer a ráno | Soukromí podle místnosti; ráno neotevírat před nastaveným časem a během režimu spánku. Časy zatím nejsou vybrané. |
| Přehřívání | Pozdější etapa: teplota konkrétní místnosti + oslunění její fasády. Nevycházet ze stavu kotle. |
| Krátké změny počasí | Návrh: stabilita podmínky 5 minut, minimálně 15 minut mezi komfortními pohyby, rozdíl cíle alespoň 10 procentních bodů. |
| Ochrana průchodu | Pokud okno slouží jako průchod, otevřený/neznámý kontakt blokuje automatické zavírání. V automatic otevření při zavírání vyvolá stop. Režim „terasa používána“ brání zavření i za člověkem venku. |
| Restart a návrat komunikace | Nejprve obnovit stav a ruční prioritu; zahodit staré příkazy, znovu vyhodnotit situaci. |
| Nedosažení cíle | Zaznamenat poruchu, blokovat komfortní opakování, nerekalibrovat automaticky. |

Dvě hodiny, 5/15 minut a 10 procentních bodů jsou výchozí návrhy pro review, nikoli naměřené parametry. Stop a ruční příkaz nečekají na komfortní prodlevy. Pět rolet je explicitní seznam; garážová vrata do něj nepatří.

## Dekompozice konfigurace

`shading_policy`: výpočet cíle a důvodu; `shading_control`: jediná cesta automatických příkazů a jejich ověření; `shading_diagnostics`: blokace, poruchy a historie. Mapování oken a prahy v jednom inventáři, obnovovaný uživatelský stav v HA helperech. Je to návrh budoucích packages, dosud neexistující soubory.

První implementace: ruční priorita, ráno/večer a případná ochrana průchodu. Tepelné stínění až po mapování fasád; vítr/mráz až podle pravidel dodavatele rolet. Ochrana přes HA nenahrazuje místní ochrany motoru.

## Co musí prokázat jeden pilotní kus

1. Elektrikář potvrdí konkrétní motor, limit 1 A, odpovídající jištění a správné řízení Somfy WT. Zvlášť prověřit největší roletu; velikost neurčuje proud motoru.
2. Zaznamenat model identifikovaný Z2M, jeho verzi, firmware zařízení a dostupné entity. Výrobce podporu Z2M deklaruje, ale konkrétní exposes musíme odečíst z dodaného kusu.
3. Zkalibrovat jednotlivé koncové polohy, změřit jízdu a zkontrolovat 0/50/100 % v obou směrech. Velká a malá roleta nesdílejí dobu jízdy.
4. Zachytit reporty při fyzickém tlačítku, ručním STOP a změně směru během automatického pohybu. Dokumentované rozhraní MINI-ZBRBS nemá samostatnou akci tlačítka; pozastavení automatiky nesmí záviset na vymyšlené události.
5. Ověřit oddělení požadovaného cíle od reportované polohy. Změna hodnoty v HA sama nedokazuje skutečný pohyb motoru.
6. Ověřit místní tlačítka bez HA/MQTT, výpadek napájení a návrat komunikace bez nechtěného dojetí starého příkazu. Nezkoušet mechanické překážky improvizovaně; postup podle dodavatele.

Bez spolehlivého rozpoznání ručního přerušení ponechat dané okno v observe. Před nákupem dalšího příslušenství ověřit i skutečný prostor a rozteče sestav.

## Testy před aktivací

V izolovaném labu spouštět skutečné HA packages proti simulovaným cover entitám: observe odesílá nulu příkazů; neaktivované okno se nehýbe; ruční priorita přežije restart; stop zruší čekající cíl; opožděný report nezpůsobí opakování; chybějící/stará čidla nevyvolají tepelný pohyb; otevřený/neznámý průchod brání zavření; garáž nikdy nedostane příkaz. Scénáře tlačítek zohlední skutečně pozorované reporty pilotu.

## Údaje, které ještě chybějí

- Místnost a orientace každé z pěti rolet, přiřazení k pozicím objednávky a jednotlivým sestavám vypínačů.
- Která roleta chrání dveře/průchod, příslušné kontakty a použitelná pokojová teplotní čidla.
- Preferované časy ráno/večer, spánkový režim a délka ruční priority.
- Přesná označení motorů, potvrzení zapojení a údaje z prvního spárovaného kusu.

Tyto neznámé údaje nebrání review návrhu ani přípravě simulace. Brání zapnutí závislých funkcí na skutečných roletách.

## Ověřené podklady

- [SONOFF Orb-ZBRBS](https://sonoff.tech/products/sonoff-fusion-series-orb-zbrbs-zigbee-smart-roller-shutter-wall-switch)
- [Manuál zakoupené varianty MINI-ZBRBS-E](https://support.sonoff.tech/mini-zbrbs-e-usermanual/)
- [Zigbee2MQTT: rozhraní MINI-ZBRBS](https://www.zigbee2mqtt.io/devices/MINI-ZBRBS.html)

Tato aktualizace kontroluje pouze dokumentaci a konzistenci inventáře. Neproběhly nové testy topení ani testy skutečných rolet.
