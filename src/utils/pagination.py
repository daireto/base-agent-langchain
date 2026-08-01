def compute_skip(page: int, size: int) -> int:
    """Compute the number of items to skip based on the current page and size."""
    return (page - 1) * size


def compute_total_pages(total: int, size: int) -> int:
    """Compute the total number of pages based on the total items and size."""
    return (total + size - 1) // size  # Ceiling division
