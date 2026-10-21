#!/usr/bin/env python3
"""Avisa por email cuando la Saucony Endorphin Azura White/Navy (talle AR 43 / US 10)
entra en descuento y tiene stock, en saucony.com.ar.

Pensado para correr cada cierto tiempo desde un workflow de GitHub Actions.
Guarda el último estado conocido en state.json y sólo manda el email cuando
el producto PASA a estar en oferta (no en cada corrida).
"""

import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

import requests

PRODUCT_URL = "https://saucony.com.ar/productos/zapatilla-hombre-endorphin-azura-white-navy/"
TARGET_SIZE_PREFIX = "US 10"  # corresponde a AR 43 en esta tienda
STATE_FILE = Path(__file__).parent / "state.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def fetch_html() -> str:
    resp = requests.get(PRODUCT_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def extract_variants(html: str) -> list:
    """Extrae el array JSON asignado a `LS.variants = [...]` en el HTML de Tienda Nube."""
    marker = "LS.variants = ["
    start = html.find(marker)
    if start == -1:
        raise RuntimeError(
            "No se encontró 'LS.variants' en el HTML. El sitio pudo haber cambiado "
            "de estructura o de plataforma."
        )

    start_bracket = start + len(marker) - 1  # posición del '[' inicial
    depth = 0
    in_string = False
    escape = False
    end = None

    for i in range(start_bracket, len(html)):
        ch = html[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break

    if end is None:
        raise RuntimeError("No se pudo encontrar el cierre del array de variantes.")

    return json.loads(html[start_bracket : end + 1])


def find_target_variant(variants: list) -> dict:
    for variant in variants:
        size_label = (variant.get("option1") or "").strip()
        first_token = size_label.split("/")[0].strip()
        if first_token == TARGET_SIZE_PREFIX:
            return variant
    raise RuntimeError(
        f"No se encontró ninguna variante de talle '{TARGET_SIZE_PREFIX}'. "
        "Talles vistos: " + ", ".join(sorted({v.get('option1', '') for v in variants}))
    )


def is_on_sale(variant: dict) -> bool:
    price = variant.get("price_number") or 0
    compare_at = variant.get("compare_at_price_number")
    has_promo = bool(variant.get("has_promotional_price"))
    discounted = bool(compare_at) and compare_at > price
    in_stock = bool(variant.get("available")) and (variant.get("stock") or 0) > 0
    return in_stock and (discounted or has_promo)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"on_sale": False}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def send_email(variant: dict) -> None:
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    email_from = os.environ.get("EMAIL_FROM", smtp_user)
    email_to = os.environ["EMAIL_TO"]

    price = variant.get("price_short", "?")
    compare_at = variant.get("compare_at_price_short")
    stock = variant.get("stock")
    size_label = variant.get("option1", "?")

    lines = [
        "¡Las Saucony Endorphin Azura entraron en descuento en talle AR 43!",
        "",
        f"Precio actual: {price}",
    ]
    if compare_at:
        lines.append(f"Precio anterior: {compare_at}")
    lines.append(f"Talle: {size_label}")
    lines.append(f"Stock disponible: {stock}")
    lines.append("")
    lines.append(PRODUCT_URL)

    body = "\n".join(lines)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Saucony Endorphin Azura en descuento (talle AR 43)"
    msg["From"] = email_from
    msg["To"] = email_to

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(email_from, [email_to], msg.as_string())


def main() -> int:
    try:
        html = fetch_html()
        variants = extract_variants(html)
        variant = find_target_variant(variants)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    on_sale_now = is_on_sale(variant)
    state = load_state()
    was_on_sale = bool(state.get("on_sale"))

    print(
        f"Talle {variant.get('option1')}: precio={variant.get('price_short')} "
        f"compare_at={variant.get('compare_at_price_short')} stock={variant.get('stock')} "
        f"on_sale={on_sale_now} (antes: {was_on_sale})"
    )

    if on_sale_now and not was_on_sale:
        print("Cambio detectado -> enviando email de aviso.")
        send_email(variant)
    elif on_sale_now:
        print("Sigue en oferta, ya se había avisado. No se reenvía email.")
    else:
        print("No está en oferta todavía.")

    save_state(
        {
            "on_sale": on_sale_now,
            "price_number": variant.get("price_number"),
            "compare_at_price_number": variant.get("compare_at_price_number"),
            "stock": variant.get("stock"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
