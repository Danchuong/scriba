"""Minimal Scriba "hello world" stub.

Imports work in Phase 1A; calling the pipeline raises NotImplementedError
until later phases land.
"""

from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer


def main() -> None:
    pool = SubprocessWorkerPool()
    tex = TexRenderer(worker_pool=pool)
    pipeline = Pipeline([tex])
    ctx = RenderContext(resource_resolver=lambda name: None)
    doc = pipeline.render("Hello, $x^2$.", ctx)
    print(doc.html)


if __name__ == "__main__":
    main()
