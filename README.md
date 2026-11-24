# Pragmatic Application Security

Statisches Blog, erzeugt mit [Antora](https://antora.org). Die Beiträge stammen aus dem WordPress-Export der alten Seite.

## Bauen

```
npm ci
npm run build      # Ergebnis: build/site
```

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
