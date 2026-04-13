#!/usr/bin/env bash
set -e

if [ ! -f "./tailwindcss" ]; then
    OS=$(uname -s)
    ARCH=$(uname -m)

    if   [ "$OS" = "Linux"  ] && [ "$ARCH" = "x86_64"  ]; then FILE="tailwindcss-linux-x64"
    elif [ "$OS" = "Linux"  ] && [ "$ARCH" = "aarch64" ]; then FILE="tailwindcss-linux-arm64"
    elif [ "$OS" = "Darwin" ] && [ "$ARCH" = "x86_64"  ]; then FILE="tailwindcss-macos-x64"
    elif [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64"   ]; then FILE="tailwindcss-macos-arm64"
    else
        echo "Unsupported platform: $OS $ARCH"
        exit 1
    fi

    echo "Downloading $FILE..."
    curl -sL "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/$FILE" -o tailwindcss
    chmod +x tailwindcss
    echo "Done."
fi

python build.py --serve --drafts
