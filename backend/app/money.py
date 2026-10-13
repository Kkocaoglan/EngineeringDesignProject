"""Para yardımcıları. Projede yuvarlama SADECE burada yapılır (CLAUDE.md kuralı).

- 8 ondalık, ROUND_HALF_EVEN (bankacı yuvarlaması).
- Çarpma/bölme yüksek hassasiyetle yapılır, sonra 8 ondalığa yuvarlanır; böylece Python'un
  varsayılan 28 basamaklı bağlamı büyük sayılarda sessizce yuvarlama yapamaz.
K1 emir motoru için açtı; K3 portföy hesabında aynı fonksiyonları kullanır ve genişletir.
"""

from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal, localcontext

EIGHT_PLACES = Decimal("0.00000001")
_PRECISION = 60


def q8(value: Decimal) -> Decimal:
    """8 ondalığa yuvarlar (ROUND_HALF_EVEN)."""
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return value.quantize(EIGHT_PLACES, rounding=ROUND_HALF_EVEN)


def mul(a: Decimal, b: Decimal) -> Decimal:
    """a × b, 8 ondalığa yuvarlanmış."""
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return q8(a * b)


def ratio_of(total: Decimal, part: Decimal, whole: Decimal) -> Decimal:
    """total × part / whole, 8 ondalığa yuvarlanmış (ör. satılan kısmın maliyeti)."""
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return q8(total * part / whole)


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    """value'yu step'in katına AŞAĞI yuvarlar (Binance stepSize kuralı)."""
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        steps = (value / step).to_integral_value(rounding=ROUND_DOWN)
        return q8(steps * step)


def fmt(value: Decimal) -> str:
    """API'de para/miktar her zaman 8 ondalıklı string: "10000.00000000"."""
    return f"{q8(value):f}"
