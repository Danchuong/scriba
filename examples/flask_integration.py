"""Flask integration stub. See ``docs/scriba/08-usage-example.md``."""

# from flask import Flask
# from scriba import Pipeline, RenderContext, SubprocessWorkerPool
# from scriba.tex import TexRenderer
#
# app = Flask(__name__)
# pool = SubprocessWorkerPool()
# pipeline = Pipeline([TexRenderer(worker_pool=pool)])
#
# @app.route("/render")
# def render():
#     ctx = RenderContext(resource_resolver=lambda name: None)
#     doc = pipeline.render(request.args["src"], ctx)
#     return doc.html
