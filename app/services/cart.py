from uuid import UUID

from app.db.client import Database


def cart_action(
    db: Database, user: dict, action: str,
    product_id: UUID | None = None, quantity: int | None = None,
) -> dict:
    # 회원 ID/인증 버전은 요청 본문이 아닌 인증된 사용자 정보에서만 가져옵니다.
    return db.rpc('shop_cart', {
        'p_user_id': str(user['id']), 'p_auth_version': user['auth_version'],
        'p_action': action, 'p_product_id': str(product_id) if product_id else None,
        'p_quantity': quantity,
    })
