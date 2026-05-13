from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from ..bootstrap import build_runtime
from ..config.rss_sources import load_rss_sources, save_rss_sources
from ..config.settings import AppSettings
from ..logging_config import configure_logging


def create_app() -> Flask:
    settings = AppSettings()
    configure_logging(settings.app_log_path)

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = "vertice-dev-secret-key"

    def build_page_context():
        runtime = build_runtime()
        repository = runtime["repository"]
        rss_sources = load_rss_sources(settings.rss_sources_path)
        return {
            "counts": repository.get_dashboard_counts(),
            "articles": repository.list_articles(limit=300),
            "stats": repository.list_source_stats(),
            "rss_sources": rss_sources,
        }

    @app.get("/")
    def dashboard():
        return render_template("dashboard.html", **build_page_context())

    @app.get("/articles")
    def articles():
        return render_template("articles.html", **build_page_context())

    @app.post("/articles/enrich")
    def enrich_articles():
        runtime = build_runtime()
        result = runtime["article_enrichment_service"].enrich_pending_articles()
        flash(
            (
                "Enriquecimento concluido. "
                f"processados={result.processed} | ignorados={result.skipped} | erros={result.errors}"
            ),
            "success",
        )
        return redirect(url_for("articles"))

    @app.post("/articles/summarize")
    def summarize_articles():
        runtime = build_runtime()
        try:
            result = runtime["article_analysis_service"].summarize_pending_articles()
            flash(
                (
                    "Resumos com Ollama concluidos. "
                    f"processados={result.processed} | ignorados={result.skipped} | erros={result.errors}"
                ),
                "success",
            )
        except Exception as exc:
            flash(f"Falha ao gerar resumos com Ollama: {exc}", "error")
        return redirect(url_for("articles"))

    @app.get("/stats")
    def stats():
        return render_template("stats.html", **build_page_context())

    @app.get("/operations")
    def operations():
        runtime = build_runtime()
        operations_dashboard = runtime["operation_stats_service"].build_dashboard()
        return render_template(
            "operations.html",
            operations_dashboard=operations_dashboard,
            **build_page_context(),
        )

    @app.get("/sources")
    def sources():
        return render_template("sources.html", **build_page_context())

    @app.post("/rss/validate")
    def validate_rss():
        runtime = build_runtime()
        rss_sources = load_rss_sources(settings.rss_sources_path)
        validation_results = runtime["feed_validator"].validate_sources(rss_sources)
        flash("Validacao de feeds concluida.", "success")
        return render_template(
            "sources.html",
            source_validations=validation_results,
            **build_page_context(),
        )

    @app.get("/database")
    def database():
        return render_template("database.html", **build_page_context())

    @app.post("/scrape")
    def scrape():
        runtime = build_runtime()
        ingestion_summary = runtime["ingestion_service"].run()
        flash("Scraping executado com sucesso.", "success")
        return render_template(
            "dashboard.html",
            scrape_summary=ingestion_summary,
            **build_page_context(),
        )

    @app.post("/rss/add")
    def add_rss():
        sources = load_rss_sources(settings.rss_sources_path)
        new_source = {
            "name": request.form.get("name", "").strip(),
            "url": request.form.get("url", "").strip(),
            "category": request.form.get("category", "").strip(),
        }

        if not new_source["name"] or not new_source["url"]:
            flash("Nome e URL do RSS sao obrigatorios.", "error")
            return redirect(url_for("sources"))

        if any(source["url"] == new_source["url"] for source in sources):
            flash("Ja existe um RSS cadastrado com essa URL.", "error")
            return redirect(url_for("sources"))

        sources.append(new_source)
        save_rss_sources(settings.rss_sources_path, sources)
        flash("RSS adicionado com sucesso.", "success")
        return redirect(url_for("sources"))

    @app.post("/rss/<int:source_index>/update")
    def update_rss(source_index: int):
        sources = load_rss_sources(settings.rss_sources_path)
        if source_index < 0 or source_index >= len(sources):
            flash("Fonte RSS nao encontrada.", "error")
            return redirect(url_for("sources"))

        updated_source = {
            "name": request.form.get("name", "").strip(),
            "url": request.form.get("url", "").strip(),
            "category": request.form.get("category", "").strip(),
        }

        if not updated_source["name"] or not updated_source["url"]:
            flash("Nome e URL do RSS sao obrigatorios.", "error")
            return redirect(url_for("sources"))

        for current_index, source in enumerate(sources):
            if current_index != source_index and source["url"] == updated_source["url"]:
                flash("Outra fonte ja usa essa URL.", "error")
                return redirect(url_for("sources"))

        sources[source_index] = updated_source
        save_rss_sources(settings.rss_sources_path, sources)
        flash("RSS atualizado com sucesso.", "success")
        return redirect(url_for("sources"))

    @app.post("/rss/<int:source_index>/delete")
    def delete_rss(source_index: int):
        sources = load_rss_sources(settings.rss_sources_path)
        if source_index < 0 or source_index >= len(sources):
            flash("Fonte RSS nao encontrada.", "error")
            return redirect(url_for("sources"))

        removed_source = sources.pop(source_index)
        save_rss_sources(settings.rss_sources_path, sources)
        flash(f"RSS removido: {removed_source['name']}", "success")
        return redirect(url_for("sources"))

    @app.post("/rss/<int:source_index>/apply-suggestion")
    def apply_rss_suggestion(source_index: int):
        sources = load_rss_sources(settings.rss_sources_path)
        if source_index < 0 or source_index >= len(sources):
            return jsonify(
                {
                    "success": False,
                    "message": "Fonte RSS nao encontrada.",
                }
            ), 404

        suggested_url = request.form.get("suggested_url", "").strip()
        if not suggested_url:
            return jsonify(
                {
                    "success": False,
                    "message": "Nenhuma URL sugerida foi enviada.",
                }
            ), 400

        for current_index, source in enumerate(sources):
            if current_index != source_index and source["url"] == suggested_url:
                return jsonify(
                    {
                        "success": False,
                        "message": "Ja existe outra fonte usando a URL sugerida.",
                    }
                ), 409

        sources[source_index]["url"] = suggested_url
        save_rss_sources(settings.rss_sources_path, sources)
        return jsonify(
            {
                "success": True,
                "message": "URL sugerida aplicada com sucesso.",
                "source_index": source_index,
                "updated_url": suggested_url,
            }
        )

    @app.post("/database/clear")
    def clear_database():
        runtime = build_runtime()
        repository = runtime["repository"]
        scope = request.form.get("scope", "articles")

        if scope == "all":
            repository.clear_all_data()
            flash("Todos os dados do banco foram apagados.", "success")
        else:
            repository.clear_articles()
            flash("Todos os artigos foram apagados do banco.", "success")

        return redirect(url_for("database"))

    return app


def run() -> None:
    settings = AppSettings()
    app = create_app()
    app.run(host=settings.web_host, port=settings.web_port, debug=False)
