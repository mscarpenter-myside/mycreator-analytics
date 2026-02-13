def standardize_media_type(row):
    p_type = str(row.get('post_type', '')).upper()
    m_type = str(row.get('media_type', '')).upper()
    
    print(f"Input: post_type={p_type}, media_type={m_type}")

    if p_type == 'REEL' or m_type in ['REEL', 'REELS', 'VIDEO']:
        return 'Reels'
    elif p_type == 'CAROUSEL_ALBUM' or m_type in ['CAROUSEL', 'CAROUSEL_ALBUM']:
        return 'Carrossel'
    else:
        return 'Imagem'

test_cases = [
    {'post_type': 'REELS', 'media_type': None},       # Suspected FAIL -> Imagem
    {'post_type': 'REELS', 'media_type': 'Reels'},    # Pass -> Reels
    {'post_type': 'FEED', 'media_type': 'Carousel'},  # Pass -> Carrossel
    {'post_type': 'FEED', 'media_type': None},        # Pass -> Imagem
    {'post_type': 'VIDEO', 'media_type': None},       # Suspected FAIL -> Imagem
    {'post_type': 'REEL', 'media_type': None},        # Pass -> Reels
]

for case in test_cases:
    result = standardize_media_type(case)
    print(f"Result: {result}\n")
