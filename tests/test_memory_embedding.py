import math
import unittest

from core.persistent_memory import LocalHashEmbeddingFunction


class LocalHashEmbeddingTests(unittest.TestCase):
    def test_embedding_is_deterministic_and_normalized(self):
        embed = LocalHashEmbeddingFunction()
        first, second = embed(["hello nova", "hello nova"])
        self.assertEqual(first, second)
        norm = math.sqrt(sum(value * value for value in first))
        self.assertAlmostEqual(norm, 1.0)

    def test_empty_text_has_zero_vector(self):
        vector = LocalHashEmbeddingFunction()([""])[0]
        self.assertEqual(sum(vector), 0.0)

    def test_chroma_compatibility_metadata_is_stable(self):
        embed = LocalHashEmbeddingFunction()
        rebuilt = embed.build_from_config(embed.get_config())
        self.assertEqual(embed.name(), "nova_local_hash")
        self.assertEqual(rebuilt.dimensions, embed.dimensions)
        self.assertEqual(embed.default_space(), "cosine")


if __name__ == "__main__":
    unittest.main()
