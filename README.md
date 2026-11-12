# Accu-Chek Instant pre Home Assistant

Vlastná integrácia pre aktuálny Home Assistant OS s lokálnym Bluetooth adaptérom (BlueZ). Po spárovaní sa automaticky pokúsi načítať Accu-Chek Instant, keď lokálny Bluetooth adaptér zachytí jeho vysielanie. V HA zobrazí najnovšie použiteľné meranie. Voliteľne ho odošle do Nightscout Lite ako `BG Check`.

## Inštalácia cez HACS

1. V HACS otvor ponuku **⋮ → Custom repositories**.
2. Pridaj `https://github.com/lukaskrnac/accu_check_instant_HA` s kategóriou **Integration**.
3. V HACS otvor **Accu-Chek Instant**, vyber **Download** a reštartuj Home Assistant. Ak si integráciu už nainštaloval ručne, sprav tento krok tiež, aby ju HACS spravoval.

HACS sleduje predvolenú vetvu `main`. Nové verzie si nainštaluješ z HACS alebo z oznámenia o dostupnej aktualizácii. Po aktualizácii reštartuj HA.

Pri ručnej inštalácii skopíruj priečinok `custom_components/accu_chek_instant` do `/config/custom_components/` a reštartuj HA.

## Nastavenie glukomera

1. Otvor **Nastavenia → Zariadenia a služby → Pridať integráciu → Accu-Chek Instant**. Zadaj Bluetooth MAC adresu glukomera a jeho šesťmiestny párovací PIN. Adresu môžeš nájsť v Bluetooth nastaveniach HA, keď glukomer vysiela. Pri existujúcom spárovaní s adaptérom HA môže PIN ostať prázdny.
2. Pri prvom použití daj glukomer do párovacieho režimu, potom v zariadení v HA stlač **Načítať meranie**. Pri ďalšom meraní v dosahu HA stačí zmerať glykémiu a vybrať prúžok ako zvyčajne. Tlačidlo môžeš použiť aj na okamžité ručné načítanie.
3. Skontroluj hodnotu aj atribút `measured_at` oproti glukomeru. Integrácia počíta s tým, že miestny čas glukomera patrí do časového pásma nastaveného v HA.

Pri aktualizácii zo staršej verzie prepíš rovnaký priečinok a reštartuj HA. Už spárovaný glukomer začne HA čítať automaticky. Na prvé párovanie sa naďalej používa tlačidlo.

Instant si pamätá jedno spárovanie. Spárovanie s HA prepíše existujúce párovanie s telefónom. Použi lokálny Bluetooth adaptér Orange Pi alebo USB adaptér pripojený k HA. Táto verzia páruje cez BlueZ, preto Bluetooth proxy nepodporuje.

## Voliteľný zápis do Nightscout Lite

V nastaveniach integrácie zadaj domácu URL Nightscout Lite pre port `1338` a jeho `write_secret`. Najprv si môžeš overiť čítanie bez zápisu a údaje doplniť cez **Prekonfigurovať**. HA použije originálny čas merania. Opakované načítanie toho istého záznamu z toho istého glukomera dostane rovnaké ID. Ak Nightscout Lite zápis odmietne, meranie zostane zobrazené v HA a zápis sa dá zopakovať tlačidlom.

Telefóny ostávajú v režime Follow na čítacej adrese. Voľba **Calibrate from BG entries** použije importované meranie, pokiaľ sa časovo spáruje s históriou CGM.

## Referencie

- [Praktický postup s ESPHome pre tento model](https://rutg3r.com/accu-chek-instant-glucose-meter-home-assistant-bluetooth/)
- [Bluetooth SIG Glucose Service](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/GLS_v1.0.1/out/en/index-en.html)
- [JugglucoNG a zvláštnosti RACP pre Instant](https://github.com/ctqvva/JugglucoNG/blob/1.3.2-Alpha/Common/src/mobile/java/tk/glucodata/GlucoseMeterGatt.java)
