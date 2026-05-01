namespace SuperSuat.Api;

public static class DictionaryExtensions
{
    public static TValue? GetValueOrDefault<TKey, TValue>(this IDictionary<TKey, TValue>? dictionary, TKey key)
        where TKey : notnull
    {
        if (dictionary == null)
            return default;

        return dictionary.TryGetValue(key, out var value) ? value : default;
    }
}
