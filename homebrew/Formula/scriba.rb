class Scriba < Formula
  include Language::Python::Virtualenv

  desc "LaTeX to animated HTML renderer for competitive programming editorials"
  homepage "https://scriba.ojcloud.dev"
  url "https://files.pythonhosted.org/packages/source/s/scriba/scriba-0.5.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "MIT"

  depends_on "python@3.12"

  resource "pygments" do
    url "https://files.pythonhosted.org/packages/source/p/pygments/pygments-2.19.1.tar.gz"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system libexec/"bin/python", "-c", "import scriba; print(scriba.__version__)"
  end
end
