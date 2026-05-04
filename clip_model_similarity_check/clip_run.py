"""
CLIP-based Image-Text Similarity Checker (merged)
Compares image content with textual descriptions to detect mismatches
Includes 3-way classification: not at all related / similar context / exact related
"""

import torch
import requests
from PIL import Image
from io import BytesIO
from transformers import CLIPProcessor, CLIPModel
import argparse
import sys


class CLIPSimilarityChecker:
    """
    A class to check similarity between images and text using CLIP model
    """

    def __init__(self, model_name="openai/clip-vit-base-patch32", threshold=0.25, similar_threshold=0.19, exact_threshold=0.25):
        """
        Initialize the CLIP model and processor

        Args:
            model_name (str): The CLIP model to use
            threshold (float): Similarity threshold for binary matching (0-1)
            similar_threshold (float): Lower bound for 'similar context' (0-1)
            exact_threshold (float): Lower bound for 'exact related' (0-1)
        """
        print(f"Loading CLIP model: {model_name}...")
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.threshold = threshold
        # thresholds for 3-way classification
        self.similar_threshold = similar_threshold
        self.exact_threshold = exact_threshold
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        print(f"Model loaded successfully on {self.device}")

    def download_image(self, image_url):
        """
        Download image from URL

        Args:
            image_url (str): URL of the image

        Returns:
            PIL.Image: Downloaded image
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert('RGB')
            return image
        except Exception as e:
            raise Exception(f"Failed to download image from {image_url}: {str(e)}")

    def get_embeddings(self, text, image):
        """
        Get CLIP embeddings for text and image

        Args:
            text (str): Text content to encode
            image (PIL.Image): Image to encode

        Returns:
            tuple: (text_embedding, image_embedding)
        """
        # Process inputs
        inputs = self.processor(
            text=[text],
            images=[image],
            return_tensors="pt",
            padding=True,
            truncation=True
        )

        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Get embeddings
        with torch.no_grad():
            outputs = self.model(**inputs)
            text_embeds = outputs.text_embeds
            image_embeds = outputs.image_embeds

        # Normalize embeddings
        text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)
        image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)

        return text_embeds, image_embeds

    def calculate_similarity(self, text_embeds, image_embeds):
        """
        Calculate cosine similarity between text and image embeddings

        Args:
            text_embeds (torch.Tensor): Text embeddings
            image_embeds (torch.Tensor): Image embeddings

        Returns:
            float: Cosine similarity score (0-1)
        """
        similarity = torch.cosine_similarity(text_embeds, image_embeds)
        return similarity.item()

    def categorize_similarity(self, similarity_score):
        """
        Map a similarity score to one of three categories:
          1 -> 'not at all related'
          2 -> 'similar context'
          3 -> 'exact related'

        Returns:
            tuple: (category_string, category_code)
        """
        if similarity_score is None:
            return (None, None)

        if similarity_score < self.similar_threshold:
            return ("not at all related", 1)
        if similarity_score < self.exact_threshold:
            return ("similar context", 2)
        return ("exact related", 3)

    def check_match(self, text, image_url, verbose=True):
        """
        Check if image and text content match

        Args:
            text (str): Text content
            image_url (str): URL of the image
            verbose (bool): Print detailed information

        Returns:
            dict: Results containing similarity score and match status
        """
        try:
            # Download image
            if verbose:
                print(f"\nDownloading image from: {image_url}")
            image = self.download_image(image_url)

            if verbose:
                print(f"Image size: {image.size}")
                print(f"Text preview: {text[:100]}...")

            # Get embeddings
            if verbose:
                print("Generating embeddings...")
            text_embeds, image_embeds = self.get_embeddings(text, image)

            # Calculate similarity
            similarity_score = self.calculate_similarity(text_embeds, image_embeds)

            # Determine if it's a match (binary) and categorize into three classes
            is_match = similarity_score >= self.threshold
            relation, relation_code = self.categorize_similarity(similarity_score)

            result = {
                'similarity_score': round(similarity_score, 4),
                'is_match': is_match,
                'threshold': self.threshold,
                'text': text,
                'image_url': image_url,
                'confidence': 'HIGH' if abs(similarity_score - self.threshold) > 0.1 else 'LOW',
                'relation': relation,
                'relation_code': relation_code
            }

            if verbose:
                print(f"\n{'='*60}")
                print(f"Similarity Score: {result['similarity_score']:.4f}")
                print(f"Threshold: {result['threshold']:.4f}")
                print(f"Match: {'✓ YES' if is_match else '✗ NO'}")
                print(f"Relation: {result['relation']} (code: {result['relation_code']})")
                print(f"Confidence: {result['confidence']}")
                print(f"{'='*60}")

            return result

        except Exception as e:
            return {
                'error': str(e),
                'similarity_score': None,
                'is_match': None
            }

    def batch_check(self, text_image_pairs):
        """
        Check multiple text-image pairs

        Args:
            text_image_pairs (list): List of (text, image_url) tuples

        Returns:
            list: List of result dictionaries
        """
        results = []
        for i, (text, image_url) in enumerate(text_image_pairs, 1):
            print(f"\n\nProcessing pair {i}/{len(text_image_pairs)}")
            result = self.check_match(text, image_url, verbose=True)
            results.append(result)

        return results


def main(argv=None):
    """Simple CLI: accept `--image-url` and `--text` (or prompt) and print score + classification."""
    parser = argparse.ArgumentParser(description="CLIP image-text similarity checker")
    parser.add_argument("--image-url", help="URL of the image to check", default=None)
    parser.add_argument("--text", help="Text/paragraph to compare with the image", default=None)
    parser.add_argument("--threshold", type=float, help="binary match threshold", default=0.25)
    parser.add_argument("--similar-threshold", type=float, help="lower bound for 'similar context'", default=0.19)
    parser.add_argument("--exact-threshold", type=float, help="lower bound for 'exact related'", default=0.25)

    args = parser.parse_args(argv)

    # Prompt interactively if missing
    image_url = args.image_url or input("Image URL: ").strip()
    text = args.text or input("Text / paragraph: ").strip()

    if not image_url:
        print("No image URL provided. Exiting.")
        sys.exit(1)
    if not text:
        print("No text provided. Exiting.")
        sys.exit(1)

    checker = CLIPSimilarityChecker(threshold=args.threshold, similar_threshold=args.similar_threshold, exact_threshold=args.exact_threshold)

    print("\nRunning similarity check...")
    result = checker.check_match(text, image_url, verbose=True)

    if 'error' in result:
        print("Error:", result['error'])
        sys.exit(1)

    print("\nResult:")
    print(f"Similarity score: {result['similarity_score']}")
    print(f"Relation: {result.get('relation')} (code {result.get('relation_code')})")
    print(f"Binary match (threshold {result['threshold']}): {'YES' if result['is_match'] else 'NO'}")


if __name__ == "__main__":
    main()
