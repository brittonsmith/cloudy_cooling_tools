def get_grid_indices(dims,index):
    "Return indices with shape of dims corresponding to scalar index."
    indices = []
    dims.reverse()
    for dim in dims:
        indices.append(index % dim)
        index -= indices[-1]
        index //= dim

    dims.reverse()
    indices.reverse()
    return indices
