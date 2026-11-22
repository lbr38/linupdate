#!/usr/bin/env bash
# Generate the changelog of the current linupdate version (version file) from its section in CHANGELOG.md
#
# Usage: generate-changelog.sh <format> <output file>
#   md  : the raw markdown section (GitHub release notes)
#   deb : a Debian changelog entry (to gzip into /usr/share/doc/linupdate/changelog.gz)
#   rpm : a %changelog entry (to append to the spec file)
#
# Fails if CHANGELOG.md has no (or an empty) section for the current version.

set -euo pipefail

FORMAT="${1:?missing format (md, deb or rpm)}"
OUTPUT="${2:?missing output file}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHANGELOG="${ROOT}/CHANGELOG.md"
VERSION="$(tr -d '[:space:]' < "${ROOT}/version")"
MAINTAINER="$(sed -n 's/^Maintainer: *//p' "${ROOT}/.github/workflows/packaging/deb/control")"
RELEASE="$(sed -n 's/^Release: *//p' "${ROOT}/.github/workflows/packaging/rpm/spec")"
WIDTH=80

# Lines between the "## <version>" heading and the next "## " heading, without the leading and trailing blank lines
NOTES="$(awk -v version="$VERSION" '/^## / { in_section = ($2 == version); next } in_section' "$CHANGELOG" | sed '/./,$!d')"

if [ -z "$(printf '%s' "$NOTES" | tr -d '[:space:]')" ];then
    echo "No release notes for version ${VERSION} in ${CHANGELOG} (expected a '## ${VERSION}' section)" >&2
    exit 1
fi

# Print <text> wrapped to $WIDTH columns, the first line prefixed with <first>, the next ones with <next> (same length)
wrap() {
    printf '%s\n' "$3" | fold -s -w $((WIDTH - ${#2})) | sed -e 's/ *$//' -e "1s/^/$1/" -e "2,\$s/^/$2/"
}

# Convert the markdown notes to plain text items: "**Section**" lines become top level items, "- item" lines nested items
# Arguments: prefixes of a top level item, of its next lines, of a nested item, of its next lines
to_text() {
    local line text in_section=0

    while IFS= read -r line; do
        line="$(printf '%s' "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        [ -n "$line" ] || continue

        # Plain text: no markdown emphasis or code marks
        text="$(printf '%s' "$line" | sed -e 's/^[-*] //' -e 's/\*\*//g' -e 's/`//g')"

        if [[ "$line" =~ ^\*\*.*\*\*$ ]];then
            in_section=1
            wrap "$1" "$2" "${text}:"
        elif [ "$in_section" -eq 1 ];then
            wrap "$3" "$4" "$text"
        else
            wrap "$1" "$2" "$text"
        fi
    done <<< "$NOTES"
}

case "$FORMAT" in
    md)
        printf '%s\n' "$NOTES" > "$OUTPUT"
        ;;
    deb)
        {
            echo "linupdate (${VERSION}) stable; urgency=medium"
            echo
            to_text '  * ' '    ' '    - ' '      '
            echo
            echo " -- ${MAINTAINER}  $(LC_ALL=C date -u -R)"
        } > "$OUTPUT"
        ;;
    rpm)
        {
            echo "* $(LC_ALL=C date -u '+%a %b %d %Y') ${MAINTAINER} - ${VERSION}-${RELEASE}"
            # '%' would be expanded as a macro in the spec file
            to_text '- ' '  ' '  - ' '    ' | sed 's/%/%%/g'
        } > "$OUTPUT"
        ;;
    *)
        echo "Unknown format: ${FORMAT} (expected md, deb or rpm)" >&2
        exit 1
        ;;
esac
