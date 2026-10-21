DraveContrast v0.1
==================

Kleurcontrast-checker volgens WCAG. Kies een tekstkleur en een achtergrond;
de app rekent de contrastverhouding uit en zegt of het voldoende is (AA/AAA),
met een live voorbeeld. Lokaal, offline, gratis (met donatie).

Starten
-------
- Dubbelklik run.bat (installeert zichzelf de eerste keer).
- Werkt het niet? start-debug.bat (toont de fout) of herstel.bat.

Gebruik
-------
- Typ een hex-code (#d4d4d4) of klik Kies... ; onder elk veld staan je
  huisstijl-kleuren om snel te prikken. Verwisselen wisselt tekst/achtergrond.
- De contrastverhouding (bijv. 4.8 : 1) en per geval voldoende/onvoldoende:
  gewone tekst AA 4.5, grote tekst AA 3.0, AAA 7.0 / 4.5, knoppen/iconen 3.0.
- Maak leesbaar (AA): past de tekstkleur iets aan tot het voldoet.

Een .exe maken (optioneel)
--------------------------
- run.bat (voor de .venv), daarna bouw-exe.bat -> dist\DraveContrast.exe.

Contact / donatie
-----------------
service@dravenlock.nl - paypal.me/roger076
