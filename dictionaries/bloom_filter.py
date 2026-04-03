"""
Bloom Filter implementation for fast dictionary word lookups.

A Bloom filter is a space-efficient probabilistic data structure that is used to test
whether an element is a member of a set. False positive matches are possible, but
false negatives are not.

This is used for quick "word not in dictionary" checks before doing more expensive
lookups, significantly reducing memory usage for large dictionaries.
"""

import math
import hashlib
from typing import Set, Optional


class BloomFilter:
    """
    Space-efficient probabilistic membership test.
    
    For a dictionary with N items and false positive rate P:
    - Required bits: M = -(N * ln(P)) / (ln(2)^2)
    - Required hash functions: K = (M/N) * ln(2)
    
    For 1.5M words with 0.1% false positive rate:
    - M ≈ 21.5 million bits ≈ 2.7 MB
    - K ≈ 10 hash functions
    """
    
    def __init__(self, expected_items: int, false_positive_rate: float = 0.001):
        """
        Initialize bloom filter.
        
        Args:
            expected_items: Expected number of items to store
            false_positive_rate: Desired false positive rate (0.001 = 0.1%)
        """
        # Calculate optimal size and number of hash functions
        self.size = self._calculate_size(expected_items, false_positive_rate)
        self.hash_count = self._calculate_hash_count(self.size, expected_items)
        
        # Initialize bit array
        self.bit_array = [False] * self.size
        self.item_count = 0
    
    @staticmethod
    def _calculate_size(n: int, p: float) -> int:
        """Calculate optimal bit array size."""
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(math.ceil(m))
    
    @staticmethod
    def _calculate_hash_count(m: int, n: int) -> int:
        """Calculate optimal number of hash functions."""
        k = (m / n) * math.log(2)
        return int(math.ceil(k))
    
    def _get_hashes(self, item: str) -> list:
        """
        Generate multiple hash values for an item.
        
        Uses double hashing technique:
        h(i) = (h1(item) + i * h2(item)) % size
        
        This is more efficient than computing K independent hashes.
        """
        # Two base hashes using different algorithms
        h1 = int(hashlib.md5(item.encode('utf-8')).hexdigest(), 16)
        h2 = int(hashlib.sha1(item.encode('utf-8')).hexdigest(), 16)
        
        hashes = []
        for i in range(self.hash_count):
            # Double hashing: h(i) = (h1 + i * h2) % size
            h = (h1 + i * h2) % self.size
            hashes.append(h)
        
        return hashes
    
    def add(self, item: str):
        """Add an item to the bloom filter."""
        item_lower = item.lower()
        for h in self._get_hashes(item_lower):
            self.bit_array[h] = True
        self.item_count += 1
    
    def contains(self, item: str) -> bool:
        """
        Check if an item might be in the set.
        
        Returns:
            True if the item is PROBABLY in the set (may be false positive)
            False if the item is DEFINITELY NOT in the set (no false negatives)
        """
        item_lower = item.lower()
        for h in self._get_hashes(item_lower):
            if not self.bit_array[h]:
                return False
        return True
    
    def populate_from_set(self, words: Set[str]):
        """
        Populate bloom filter from a set of words.
        
        This is more memory-efficient than keeping the full set in memory
        for membership tests.
        """
        for word in words:
            self.add(word)
    
    def get_stats(self) -> dict:
        """Get bloom filter statistics."""
        bits_set = sum(1 for b in self.bit_array if b)
        return {
            'size_bits': self.size,
            'size_bytes': self.size // 8,
            'size_mb': self.size / (8 * 1024 * 1024),
            'hash_count': self.hash_count,
            'item_count': self.item_count,
            'bits_set': bits_set,
            'fill_ratio': bits_set / self.size if self.size > 0 else 0
        }
