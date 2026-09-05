module InnerProductMax

export AbstractInnerProductMax, query_all
abstract type AbstractInnerProductMax{T<:Real} end

function query_all(ds::AbstractInnerProductMax{T}, queries::Matrix{T}) where {T}
    res = zero(queries)
    for (i, q) in enumrate(eachcol(queries))
        res[:, i] = query(ds, Point3{T}(q))
    end
    res
end

end