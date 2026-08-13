# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""QR code SVG rendering for TOTP enrollment.

Renders the ``otpauth://`` provisioning URI as an inline SVG using the
``qrcode`` package's SVG factory. Deliberately avoids Pillow / raster
image formats and any client-side JS QR library, keeping CSP clean
(research.md §2).
"""

import io

import qrcode
import qrcode.image.svg


def render_qr_svg(data: str) -> str:
    """Render arbitrary data (the otpauth:// provisioning URI) as an inline SVG.

    Args:
        data: The string to encode (typically a provisioning URI)

    Returns:
        UTF-8 SVG markup as a string
    """
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")
