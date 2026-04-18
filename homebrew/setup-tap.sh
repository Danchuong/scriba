#!/usr/bin/env bash
set -euo pipefail

# setup-tap.sh
# Creates the ojcloud/homebrew-tap repository structure and copies the formula.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAP_DIR="${1:-$(pwd)/homebrew-tap}"

echo "==> Creating Homebrew tap structure at: ${TAP_DIR}"

mkdir -p "${TAP_DIR}/Formula"

cp "${SCRIPT_DIR}/Formula/scriba.rb" "${TAP_DIR}/Formula/scriba.rb"

cat > "${TAP_DIR}/README.md" << 'TAPREADME'
# ojcloud/homebrew-tap

Homebrew formulae for OJCloud projects.

## Usage

```bash
brew tap ojcloud/tap
brew install scriba
```

## Available Formulae

| Formula | Description |
|---------|-------------|
| `scriba` | LaTeX to animated HTML renderer for competitive programming editorials |
TAPREADME

cd "${TAP_DIR}"
git init
git add -A
git commit -m "feat: add scriba formula"

echo ""
echo "==> Done. Next steps:"
echo ""
echo "  1. Create a GitHub repo named 'ojcloud/homebrew-tap'"
echo "  2. Push this directory to that repo:"
echo ""
echo "     cd ${TAP_DIR}"
echo "     git remote add origin git@github.com:ojcloud/homebrew-tap.git"
echo "     git push -u origin main"
echo ""
echo "  3. Update the sha256 in Formula/scriba.rb after uploading to PyPI:"
echo ""
echo "     curl -sL https://files.pythonhosted.org/packages/source/s/scriba/scriba-0.5.0.tar.gz | shasum -a 256"
echo ""
echo "  4. Users can then install with:"
echo ""
echo "     brew tap ojcloud/tap"
echo "     brew install scriba"
echo ""
