# Maintainer: CachyOS User <user@example.com>
pkgname=news-aggregator
pkgver=1.0.0
pkgrel=1
pkgdesc="Aggregatore di feed RSS/Atom in formato solo testo, integrato KDE Plasma / Breeze Dark"
arch=('any')
url="https://news-aggregator.local"
license=('GPL-3.0-or-later')
depends=(
    'python>=3.12'
    'python-pyside6>=6.10.1'
    'python-feedparser>=6.0.10'
    'python-requests>=2.31.0'
    'python-brotli>=1.0.9'
    'noto-fonts'
)
makedepends=('python-setuptools' 'python-build' 'python-installer' 'python-wheel')
optdepends=(
    'sarasa-fonts: font monospace per output tecnico'
)
source=("${pkgname}-${pkgver}.tar.gz::https://news-aggregator.local/archive/${pkgname}-${pkgver}.tar.gz")
sha256sums=('SKIP')

build() {
    cd "${srcdir}/${pkgname}-${pkgver}"
    python -m build --wheel --no-isolation
}

package() {
    cd "${srcdir}/${pkgname}-${pkgver}"

    # Installa il wheel Python
    python -m installer --destdir="${pkgdir}" dist/*.whl

    # Eseguibile wrapper in /usr/bin
    install -Dm755 /dev/stdin "${pkgdir}/usr/bin/${pkgname}" << EOF
#!/bin/sh
exec /usr/bin/python -m news_aggregator "\$@"
EOF

    # Icona SVG in /usr/share/icons/hicolor/scalable/apps/
    install -Dm644 "assets/icons/${pkgname}.svg" \
        "${pkgdir}/usr/share/icons/hicolor/scalable/apps/${pkgname}.svg"

    # File .desktop con percorsi assoluti
    install -Dm644 /dev/stdin \
        "${pkgdir}/usr/share/applications/${pkgname}.desktop" << EOF
[Desktop Entry]
Version=1.5
Type=Application
Name=News Aggregator
Name[it]=News Aggregator
Name[en]=News Aggregator
Comment=Aggregatore di feed RSS/Atom in formato solo testo
Comment[it]=Aggregatore di feed RSS/Atom in formato solo testo
Comment[en]=Text-only RSS/Atom feed aggregator
Exec=/usr/bin/${pkgname}
Icon=${pkgname}
Terminal=false
Categories=Network;News;Qt;
StartupWMClass=News Aggregator
Keywords=rss;atom;feed;news;aggregator;
EOF

    # Licenza
    install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE" 2>/dev/null || true
}
