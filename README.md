# Pragmatic Application Security

Statisches Blog, erzeugt mit [Antora](https://antora.org). Die Beiträge stammen aus dem WordPress-Export der alten Seite.

## Bauen

```
make build         # installiert Antora beim ersten Mal und erzeugt build/site
make serve         # baut und startet die Seite lokal auf http://127.0.0.1:8000
make help          # alle Ziele
```

Voraussetzungen: Node.js, npm, make und Python 3 (nur für `make serve`). `PORT=8080 make serve` ändert den Port. Der Server bindet nur an 127.0.0.1.

## Neuer Beitrag

Datei `content/modules/ROOT/pages/JJJJ/MM/TT/slug.adoc` anlegen. Die URL ist dann `/JJJJ/MM/TT/slug/`. Startseite, Tag- und Kategorieseiten erzeugt `extensions/blog.js` beim Build aus dem Dateikopf:

```
= Titel
:page-date: 2026-01-31
:page-categories: Secure Software Development
:page-tags: SAST, DevSecOps
:description: Ein bis zwei Sätze für Startseite und Suchmaschinen.
```

Bilder liegen unter `content/modules/ROOT/images/JJJJ/MM/` und werden mit `image::JJJJ/MM/datei.png[Alt-Text]` eingebunden.

## Aufbau

- `content/`: Beiträge, Bilder, Anhänge
- `ui/`: eigenes Layout und CSS, ohne JavaScript und ohne externe Ressourcen
- `extensions/blog.js`: Antora-Extension für Übersichtsseiten
- `tools/wp-import/`: einmaliger Import aus dem WordPress-SQL-Dump, siehe Kopf von `wp_import.py`
