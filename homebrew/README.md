# Homebrew Tap for Scriba

This directory contains the Homebrew formula and tooling needed to publish
Scriba via a custom Homebrew tap (`ojcloud/homebrew-tap`).

## Overview

Homebrew taps are GitHub repositories that follow the naming convention
`<org>/homebrew-<name>`. Users reference them as `<org>/<name>`.

For Scriba the tap repo is **`ojcloud/homebrew-tap`**, referenced as
`ojcloud/tap`.

## Setting Up the Tap Repository

### Option 1: Automated

```bash
chmod +x setup-tap.sh
./setup-tap.sh /path/to/homebrew-tap
```

This creates the repo structure, copies the formula, and initializes a git
repo. Follow the printed instructions to push to GitHub.

### Option 2: Manual

1. Create a new GitHub repository named **`ojcloud/homebrew-tap`**.
2. Copy `Formula/scriba.rb` into the repo at `Formula/scriba.rb`.
3. Commit and push.

## Updating the SHA256 After PyPI Upload

After publishing scriba 0.5.0 to PyPI, compute the checksum of the sdist
tarball and update the formula:

```bash
# Download and hash the sdist
curl -sL https://files.pythonhosted.org/packages/source/s/scriba/scriba-0.5.0.tar.gz \
  | shasum -a 256

# Also hash the pygments dependency (check the exact version on PyPI)
curl -sL https://files.pythonhosted.org/packages/source/p/pygments/pygments-2.19.1.tar.gz \
  | shasum -a 256
```

Replace every `REPLACE_WITH_ACTUAL_SHA256` in `Formula/scriba.rb` with the
real values.

Alternatively, use `brew create` to auto-populate:

```bash
brew create https://files.pythonhosted.org/packages/source/s/scriba/scriba-0.5.0.tar.gz
```

## User Installation

```bash
brew tap ojcloud/tap
brew install scriba
```

## Verifying the Installation

```bash
brew test scriba
```

This runs the formula's test block, which imports the `scriba` package and
prints its version.

## Updating for New Releases

When releasing a new version:

1. Update `url` in `Formula/scriba.rb` with the new version tarball URL.
2. Update all `sha256` values (scriba + each resource).
3. Update any resource version URLs if dependency versions changed.
4. Commit and push to the `ojcloud/homebrew-tap` repository.
5. Users update with `brew upgrade scriba`.
