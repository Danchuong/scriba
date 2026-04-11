# NOTE: Scriba is pre-release. This formula is a TEMPLATE; the SHA-256
# values below will be populated at the first public PyPI release. Do
# NOT ship this formula as-is — `brew install` will fail at the download
# step because the placeholder checksums cannot be verified.
#
# Pending items before this formula goes live:
#   - Confirm `url` points at the real published sdist on PyPI.
#   - Replace every REPLACE_WITH_ACTUAL_SHA256 with the actual hash.
#   - Confirm the pygments resource version matches the floor in
#     pyproject.toml (`pygments>=2.17,<2.20`).
#   - Run `brew audit --strict --online scriba` against the ojcloud tap
#     before pushing.
#
# See homebrew/README.md for the publishing workflow.

class Scriba < Formula
  include Language::Python::Virtualenv

  desc "LaTeX to animated HTML renderer for competitive programming editorials"
  homepage "https://scriba.ojcloud.dev"
  url "https://files.pythonhosted.org/packages/source/s/scriba/scriba-0.5.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"  # pending first public release
  license "MIT"

  # Scriba's pyproject.toml floor is Python 3.10. We pin the formula to
  # the current Homebrew-default CPython, but any `python@3.10+` will
  # work at runtime. Bump this when the Homebrew default advances.
  depends_on "python@3.12"

  # Node.js 18+ is required by the KaTeX subprocess worker. KaTeX itself
  # is vendored inside the wheel, so no npm install is needed.
  depends_on "node"

  resource "pygments" do
    url "https://files.pythonhosted.org/packages/source/p/pygments/pygments-2.19.1.tar.gz"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"  # pending first public release
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system libexec/"bin/python", "-c", "import scriba; print(scriba.__version__)"
  end
end
