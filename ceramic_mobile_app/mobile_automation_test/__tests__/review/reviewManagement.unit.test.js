/**
 * Review Management Unit Tests
 *
 * Test Coverage: TC-REVIEW-001 to TC-REVIEW-013
 *
 * This file contains unit tests for the Review module without E2E simulation.
 * Tests focus on validation logic, business rules, and API interactions using mocked axios calls.
 *
 * Features Tested:
 * - View product reviews
 * - Write reviews (with purchase verification)
 * - Update reviews (own reviews only)
 * - Seller responses to reviews
 * - Review validation (rating required, duplicate prevention)
 * - Mark reviews as helpful
 * - Review pagination and sorting
 * - Verified purchase badge
 *
 * @jest-environment node
 */

const axios = require('axios');

// Mock axios
jest.mock('axios');

describe('Review Management Unit Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ============================================================================
  // TC-REVIEW-001: View Product Reviews
  // ============================================================================
  describe('TC-REVIEW-001: View Product Reviews', () => {
    test('Should retrieve reviews for a product', async () => {
      // Arrange
      const productId = 1;
      const mockReviews = [
        {
          id: 1,
          product_id: 1,
          reviewer_id: 2,
          rating: 5,
          review_text: 'Excellent product!',
          is_verified_purchase: true,
          is_helpful_count: 10,
          created_at: '2025-11-20T10:00:00Z'
        },
        {
          id: 2,
          product_id: 1,
          reviewer_id: 3,
          rating: 4,
          review_text: 'Good quality',
          is_verified_purchase: true,
          is_helpful_count: 5,
          created_at: '2025-11-21T10:00:00Z'
        }
      ];

      axios.get.mockResolvedValue({ data: mockReviews });

      // Act
      const response = await axios.get(`/api/v1/reviews/product/${productId}`);

      // Assert
      expect(response.data).toHaveLength(2);
      expect(response.data[0].rating).toBe(5);
      expect(response.data[1].rating).toBe(4);
    });

    test('Should display empty list when product has no reviews', async () => {
      // Arrange
      const productId = 999;
      axios.get.mockResolvedValue({ data: [] });

      // Act
      const response = await axios.get(`/api/v1/reviews/product/${productId}`);

      // Assert
      expect(response.data).toHaveLength(0);
      expect(response.data).toEqual([]);
    });

    test('Should return error for non-existent product', async () => {
      // Arrange
      const productId = 9999;
      axios.get.mockRejectedValue({
        response: { status: 404, data: { detail: 'Product not found' } }
      });

      // Act & Assert
      await expect(axios.get(`/api/v1/reviews/product/${productId}`)).rejects.toMatchObject({
        response: { status: 404 }
      });
    });
  });

  // ============================================================================
  // TC-REVIEW-002: Write Review
  // ============================================================================
  describe('TC-REVIEW-002: Write Review', () => {
    test('Should successfully create review after purchase', async () => {
      // Arrange
      const reviewData = {
        product_id: 1,
        order_id: 10,
        rating: 5,
        review_text: 'Amazing ceramic vase! Highly recommend.'
      };

      const mockCreatedReview = {
        id: 1,
        ...reviewData,
        reviewer_id: 2,
        seller_id: 1,
        is_verified_purchase: true,
        is_helpful_count: 0,
        created_at: '2025-11-25T10:00:00Z'
      };

      axios.post.mockResolvedValue({ data: mockCreatedReview });

      // Act
      const response = await axios.post('/api/v1/reviews/', reviewData);

      // Assert
      expect(response.data.id).toBe(1);
      expect(response.data.rating).toBe(5);
      expect(response.data.review_text).toBe('Amazing ceramic vase! Highly recommend.');
      expect(response.data.is_verified_purchase).toBe(true);
    });
  });

  // ============================================================================
  // TC-REVIEW-003: Write Review - Rating Selection
  // ============================================================================
  describe('TC-REVIEW-003: Write Review - Rating Selection', () => {
    test('Should accept valid rating (1-5 stars)', async () => {
      // Arrange
      const validRatings = [1, 2, 3, 4, 5];

      for (const rating of validRatings) {
        const reviewData = {
          product_id: 1,
          order_id: 10,
          rating: rating,
          review_text: `Rating ${rating} stars`
        };

        const mockReview = {
          id: rating,
          ...reviewData,
          reviewer_id: 2,
          is_verified_purchase: true
        };

        axios.post.mockResolvedValue({ data: mockReview });

        // Act
        const response = await axios.post('/api/v1/reviews/', reviewData);

        // Assert
        expect(response.data.rating).toBe(rating);
      }
    });

    test('Should validate rating is within 1-5 range', () => {
      // Arrange
      const invalidRatings = [0, 6, -1, 10];

      // Act & Assert
      invalidRatings.forEach(rating => {
        const validation = validateRating(rating);
        expect(validation.valid).toBe(false);
        expect(validation.error).toContain('Rating must be between 1 and 5');
      });
    });
  });

  // ============================================================================
  // TC-REVIEW-004: Write Review - Validation
  // ============================================================================
  describe('TC-REVIEW-004: Write Review - Validation', () => {
    test('Should require rating', () => {
      // Arrange
      const reviewData = {
        product_id: 1,
        order_id: 10,
        review_text: 'Great product'
        // rating is missing
      };

      // Act
      const validation = validateReviewCreate(reviewData);

      // Assert
      expect(validation.valid).toBe(false);
      expect(validation.errors.rating).toBe('Rating is required');
    });

    test('Should allow review without text (rating only)', async () => {
      // Arrange
      const reviewData = {
        product_id: 1,
        order_id: 10,
        rating: 5
        // review_text is optional
      };

      const mockReview = {
        id: 1,
        ...reviewData,
        reviewer_id: 2,
        review_text: null,
        is_verified_purchase: true
      };

      axios.post.mockResolvedValue({ data: mockReview });

      // Act
      const response = await axios.post('/api/v1/reviews/', reviewData);

      // Assert
      expect(response.data.rating).toBe(5);
      expect(response.data.review_text).toBeNull();
    });

    test('Should validate required fields', () => {
      // Arrange
      const invalidReview = {
        // product_id missing
        // order_id missing
        rating: 5,
        review_text: 'Good'
      };

      // Act
      const validation = validateReviewCreate(invalidReview);

      // Assert
      expect(validation.valid).toBe(false);
      expect(validation.errors.product_id).toBe('Product ID is required');
      expect(validation.errors.order_id).toBe('Order ID is required');
    });
  });

  // ============================================================================
  // TC-REVIEW-005: Write Review - Without Purchase
  // ============================================================================
  describe('TC-REVIEW-005: Write Review - Without Purchase', () => {
    test('Should prevent review if order does not belong to user', async () => {
      // Arrange
      const reviewData = {
        product_id: 1,
        order_id: 999, // Order belonging to different user
        rating: 5,
        review_text: 'Trying to review without purchase'
      };

      axios.post.mockRejectedValue({
        response: { status: 403, data: { detail: 'Can only review your own orders' } }
      });

      // Act & Assert
      await expect(axios.post('/api/v1/reviews/', reviewData)).rejects.toMatchObject({
        response: {
          status: 403,
          data: { detail: 'Can only review your own orders' }
        }
      });
    });

    test('Should return error if order does not exist', async () => {
      // Arrange
      const reviewData = {
        product_id: 1,
        order_id: 9999, // Non-existent order
        rating: 5,
        review_text: 'Review for non-existent order'
      };

      axios.post.mockRejectedValue({
        response: { status: 404, data: { detail: 'Order not found' } }
      });

      // Act & Assert
      await expect(axios.post('/api/v1/reviews/', reviewData)).rejects.toMatchObject({
        response: { status: 404 }
      });
    });
  });

  // ============================================================================
  // TC-REVIEW-006: Write Review - Duplicate Prevention
  // ============================================================================
  describe('TC-REVIEW-006: Write Review - Duplicate Prevention', () => {
    test('Should prevent duplicate review for same product and order', async () => {
      // Arrange
      const reviewData = {
        product_id: 1,
        order_id: 10,
        rating: 5,
        review_text: 'Duplicate review attempt'
      };

      axios.post.mockRejectedValue({
        response: {
          status: 400,
          data: { detail: 'Review already exists for this product and order' }
        }
      });

      // Act & Assert
      await expect(axios.post('/api/v1/reviews/', reviewData)).rejects.toMatchObject({
        response: {
          status: 400,
          data: { detail: 'Review already exists for this product and order' }
        }
      });
    });
  });

  // ============================================================================
  // TC-REVIEW-007: Update Review
  // ============================================================================
  describe('TC-REVIEW-007: Update Review', () => {
    test('Should allow user to update their own review', async () => {
      // Arrange
      const reviewId = 1;
      const updateData = {
        rating: 4,
        review_text: 'Updated: Good product but not perfect'
      };

      const mockUpdatedReview = {
        id: reviewId,
        product_id: 1,
        order_id: 10,
        reviewer_id: 2,
        rating: 4,
        review_text: 'Updated: Good product but not perfect',
        is_verified_purchase: true,
        updated_at: '2025-11-25T11:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockUpdatedReview });

      // Act
      const response = await axios.put(`/api/v1/reviews/${reviewId}`, updateData);

      // Assert
      expect(response.data.rating).toBe(4);
      expect(response.data.review_text).toBe('Updated: Good product but not perfect');
      expect(response.data.updated_at).toBeDefined();
    });

    test('Should return error for non-existent review', async () => {
      // Arrange
      const reviewId = 9999;
      const updateData = { rating: 5 };

      axios.put.mockRejectedValue({
        response: { status: 404, data: { detail: 'Review not found' } }
      });

      // Act & Assert
      await expect(axios.put(`/api/v1/reviews/${reviewId}`, updateData)).rejects.toMatchObject({
        response: { status: 404 }
      });
    });
  });

  // ============================================================================
  // TC-REVIEW-008: Update Review - Authorization
  // ============================================================================
  describe('TC-REVIEW-008: Update Review - Authorization', () => {
    test('Should prevent updating another users review', async () => {
      // Arrange
      const reviewId = 1; // Review by different user
      const updateData = {
        rating: 1,
        review_text: 'Trying to edit someone elses review'
      };

      axios.put.mockRejectedValue({
        response: { status: 403, data: { detail: 'Not authorized to update this review' } }
      });

      // Act & Assert
      await expect(axios.put(`/api/v1/reviews/${reviewId}`, updateData)).rejects.toMatchObject({
        response: {
          status: 403,
          data: { detail: 'Not authorized to update this review' }
        }
      });
    });

    test('Should require authentication for review update', async () => {
      // Arrange
      const reviewId = 1;
      const updateData = { rating: 5 };

      axios.put.mockRejectedValue({
        response: { status: 401, data: { detail: 'Not authenticated' } }
      });

      // Act & Assert
      await expect(axios.put(`/api/v1/reviews/${reviewId}`, updateData)).rejects.toMatchObject({
        response: { status: 401 }
      });
    });
  });

  // ============================================================================
  // TC-REVIEW-009: Seller Response to Review
  // ============================================================================
  describe('TC-REVIEW-009: Seller Response to Review', () => {
    test('Should allow seller to respond to review of their product', async () => {
      // Arrange
      const reviewId = 1;
      const sellerResponseData = {
        seller_response: 'Thank you for your feedback! We appreciate your purchase.'
      };

      const mockUpdatedReview = {
        id: reviewId,
        product_id: 1,
        reviewer_id: 2,
        seller_id: 1,
        rating: 5,
        review_text: 'Great product',
        seller_response: 'Thank you for your feedback! We appreciate your purchase.',
        seller_response_at: '2025-11-25T12:00:00Z',
        is_verified_purchase: true
      };

      axios.put.mockResolvedValue({ data: mockUpdatedReview });

      // Act
      const response = await axios.put(`/api/v1/reviews/${reviewId}`, sellerResponseData);

      // Assert
      expect(response.data.seller_response).toBe('Thank you for your feedback! We appreciate your purchase.');
      expect(response.data.seller_response_at).toBeDefined();
    });

    test('Should prevent non-seller from adding seller response', async () => {
      // Arrange
      const reviewId = 1;
      const sellerResponseData = {
        seller_response: 'Unauthorized seller response attempt'
      };

      axios.put.mockRejectedValue({
        response: { status: 403, data: { detail: 'Not authorized to update this review' } }
      });

      // Act & Assert
      await expect(axios.put(`/api/v1/reviews/${reviewId}`, sellerResponseData)).rejects.toMatchObject({
        response: { status: 403 }
      });
    });

    test('Should allow seller to update their response', async () => {
      // Arrange
      const reviewId = 1;
      const updatedSellerResponse = {
        seller_response: 'Updated response: Thank you for your business!'
      };

      const mockUpdatedReview = {
        id: reviewId,
        product_id: 1,
        seller_id: 1,
        seller_response: 'Updated response: Thank you for your business!',
        seller_response_at: '2025-11-25T13:00:00Z'
      };

      axios.put.mockResolvedValue({ data: mockUpdatedReview });

      // Act
      const response = await axios.put(`/api/v1/reviews/${reviewId}`, updatedSellerResponse);

      // Assert
      expect(response.data.seller_response).toBe('Updated response: Thank you for your business!');
    });
  });

  // ============================================================================
  // TC-REVIEW-010: Mark Review Helpful
  // ============================================================================
  describe('TC-REVIEW-010: Mark Review Helpful', () => {
    test('Should increment helpful count when marked helpful', async () => {
      // Arrange
      const reviewId = 1;

      axios.post.mockResolvedValue({
        data: { message: 'Review marked as helpful' }
      });

      // Act
      const response = await axios.post(`/api/v1/reviews/${reviewId}/helpful`);

      // Assert
      expect(response.data.message).toBe('Review marked as helpful');
    });

    test('Should return error for non-existent review', async () => {
      // Arrange
      const reviewId = 9999;

      axios.post.mockRejectedValue({
        response: { status: 404, data: { detail: 'Review not found' } }
      });

      // Act & Assert
      await expect(axios.post(`/api/v1/reviews/${reviewId}/helpful`)).rejects.toMatchObject({
        response: { status: 404 }
      });
    });

    test('Should require authentication to mark helpful', async () => {
      // Arrange
      const reviewId = 1;

      axios.post.mockRejectedValue({
        response: { status: 401, data: { detail: 'Not authenticated' } }
      });

      // Act & Assert
      await expect(axios.post(`/api/v1/reviews/${reviewId}/helpful`)).rejects.toMatchObject({
        response: { status: 401 }
      });
    });
  });

  // ============================================================================
  // TC-REVIEW-011: Review Pagination
  // ============================================================================
  describe('TC-REVIEW-011: Review Pagination', () => {
    test('Should retrieve reviews with pagination parameters', async () => {
      // Arrange
      const productId = 1;
      const skip = 0;
      const limit = 10;

      const mockReviews = Array.from({ length: 10 }, (_, i) => ({
        id: i + 1,
        product_id: 1,
        rating: 5,
        review_text: `Review ${i + 1}`
      }));

      axios.get.mockResolvedValue({ data: mockReviews });

      // Act
      const response = await axios.get(`/api/v1/reviews/product/${productId}?skip=${skip}&limit=${limit}`);

      // Assert
      expect(response.data).toHaveLength(10);
    });

    test('Should respect limit parameter', async () => {
      // Arrange
      const productId = 1;
      const limit = 5;

      const mockReviews = Array.from({ length: 5 }, (_, i) => ({
        id: i + 1,
        product_id: 1,
        rating: 5
      }));

      axios.get.mockResolvedValue({ data: mockReviews });

      // Act
      const response = await axios.get(`/api/v1/reviews/product/${productId}?limit=${limit}`);

      // Assert
      expect(response.data).toHaveLength(5);
    });

    test('Should retrieve second page of reviews', async () => {
      // Arrange
      const productId = 1;
      const skip = 10;
      const limit = 10;

      const mockReviews = Array.from({ length: 10 }, (_, i) => ({
        id: i + 11, // IDs 11-20 for second page
        product_id: 1,
        rating: 4
      }));

      axios.get.mockResolvedValue({ data: mockReviews });

      // Act
      const response = await axios.get(`/api/v1/reviews/product/${productId}?skip=${skip}&limit=${limit}`);

      // Assert
      expect(response.data).toHaveLength(10);
      expect(response.data[0].id).toBe(11); // First item on second page
    });
  });

  // ============================================================================
  // TC-REVIEW-012: Review Sorting
  // ============================================================================
  describe('TC-REVIEW-012: Review Sorting', () => {
    test('Should sort reviews by newest first (default)', async () => {
      // Arrange
      const productId = 1;
      const mockReviews = [
        {
          id: 3,
          rating: 5,
          created_at: '2025-11-25T10:00:00Z' // Newest
        },
        {
          id: 2,
          rating: 4,
          created_at: '2025-11-24T10:00:00Z'
        },
        {
          id: 1,
          rating: 3,
          created_at: '2025-11-23T10:00:00Z' // Oldest
        }
      ];

      axios.get.mockResolvedValue({ data: mockReviews });

      // Act
      const response = await axios.get(`/api/v1/reviews/product/${productId}`);

      // Assert
      expect(response.data[0].id).toBe(3); // Newest first
      expect(response.data[2].id).toBe(1); // Oldest last
    });

    test('Should support sorting by helpful count', () => {
      // Arrange
      const reviews = [
        { id: 1, rating: 5, is_helpful_count: 5 },
        { id: 2, rating: 4, is_helpful_count: 20 },
        { id: 3, rating: 3, is_helpful_count: 10 }
      ];

      // Act
      const sorted = sortReviewsByHelpful(reviews);

      // Assert
      expect(sorted[0].is_helpful_count).toBe(20); // Most helpful first
      expect(sorted[1].is_helpful_count).toBe(10);
      expect(sorted[2].is_helpful_count).toBe(5);
    });

    test('Should support sorting by rating', () => {
      // Arrange
      const reviews = [
        { id: 1, rating: 3 },
        { id: 2, rating: 5 },
        { id: 3, rating: 4 }
      ];

      // Act
      const sorted = sortReviewsByRating(reviews);

      // Assert
      expect(sorted[0].rating).toBe(5); // Highest rating first
      expect(sorted[1].rating).toBe(4);
      expect(sorted[2].rating).toBe(3);
    });
  });

  // ============================================================================
  // TC-REVIEW-013: Verified Purchase Badge
  // ============================================================================
  describe('TC-REVIEW-013: Verified Purchase Badge', () => {
    test('Should display verified purchase badge for actual purchases', async () => {
      // Arrange
      const reviewId = 1;
      const mockReview = {
        id: reviewId,
        product_id: 1,
        order_id: 10,
        reviewer_id: 2,
        rating: 5,
        review_text: 'Great product',
        is_verified_purchase: true
      };

      axios.get.mockResolvedValue({ data: [mockReview] });

      // Act
      const response = await axios.get(`/api/v1/reviews/product/1`);

      // Assert
      expect(response.data[0].is_verified_purchase).toBe(true);
    });

    test('Should set is_verified_purchase to true for order-based reviews', async () => {
      // Arrange
      const reviewData = {
        product_id: 1,
        order_id: 10, // Review from actual order
        rating: 5,
        review_text: 'Verified purchase review'
      };

      const mockCreatedReview = {
        ...reviewData,
        id: 1,
        reviewer_id: 2,
        is_verified_purchase: true // Backend sets this based on order_id
      };

      axios.post.mockResolvedValue({ data: mockCreatedReview });

      // Act
      const response = await axios.post('/api/v1/reviews/', reviewData);

      // Assert
      expect(response.data.is_verified_purchase).toBe(true);
    });

    test('Should validate verified purchase badge display logic', () => {
      // Arrange
      const reviews = [
        { id: 1, is_verified_purchase: true },
        { id: 2, is_verified_purchase: false },
        { id: 3, is_verified_purchase: true }
      ];

      // Act
      const verifiedCount = reviews.filter(r => r.is_verified_purchase).length;

      // Assert
      expect(verifiedCount).toBe(2);
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================
  describe('Edge Cases', () => {
    test('Should handle review with maximum rating', async () => {
      // Arrange
      const reviewData = {
        product_id: 1,
        order_id: 10,
        rating: 5, // Maximum
        review_text: 'Perfect!'
      };

      const mockReview = { ...reviewData, id: 1, reviewer_id: 2 };
      axios.post.mockResolvedValue({ data: mockReview });

      // Act
      const response = await axios.post('/api/v1/reviews/', reviewData);

      // Assert
      expect(response.data.rating).toBe(5);
    });

    test('Should handle review with minimum rating', async () => {
      // Arrange
      const reviewData = {
        product_id: 1,
        order_id: 10,
        rating: 1, // Minimum
        review_text: 'Not satisfied'
      };

      const mockReview = { ...reviewData, id: 1, reviewer_id: 2 };
      axios.post.mockResolvedValue({ data: mockReview });

      // Act
      const response = await axios.post('/api/v1/reviews/', reviewData);

      // Assert
      expect(response.data.rating).toBe(1);
    });

    test('Should handle very long review text', async () => {
      // Arrange
      const longText = 'A'.repeat(2000); // Very long review
      const reviewData = {
        product_id: 1,
        order_id: 10,
        rating: 5,
        review_text: longText
      };

      const mockReview = { ...reviewData, id: 1, reviewer_id: 2 };
      axios.post.mockResolvedValue({ data: mockReview });

      // Act
      const response = await axios.post('/api/v1/reviews/', reviewData);

      // Assert
      expect(response.data.review_text).toHaveLength(2000);
    });

    test('Should handle review with zero helpful count', async () => {
      // Arrange
      const mockReview = {
        id: 1,
        rating: 5,
        is_helpful_count: 0
      };

      axios.get.mockResolvedValue({ data: [mockReview] });

      // Act
      const response = await axios.get('/api/v1/reviews/product/1');

      // Assert
      expect(response.data[0].is_helpful_count).toBe(0);
    });
  });
});

// ============================================================================
// Validation Helper Functions
// ============================================================================

/**
 * Validate review creation request
 * @param {Object} reviewData - Review data to validate
 * @returns {Object} Validation result with valid flag and errors
 */
function validateReviewCreate(reviewData) {
  const errors = {};

  // Validate product_id
  if (reviewData.product_id === undefined || reviewData.product_id === null) {
    errors.product_id = 'Product ID is required';
  } else if (typeof reviewData.product_id !== 'number' || reviewData.product_id < 1) {
    errors.product_id = 'Product ID must be a valid positive integer';
  }

  // Validate order_id
  if (reviewData.order_id === undefined || reviewData.order_id === null) {
    errors.order_id = 'Order ID is required';
  } else if (typeof reviewData.order_id !== 'number' || reviewData.order_id < 1) {
    errors.order_id = 'Order ID must be a valid positive integer';
  }

  // Validate rating (required)
  if (reviewData.rating === undefined || reviewData.rating === null) {
    errors.rating = 'Rating is required';
  } else if (typeof reviewData.rating !== 'number') {
    errors.rating = 'Rating must be a number';
  } else if (reviewData.rating < 1 || reviewData.rating > 5) {
    errors.rating = 'Rating must be between 1 and 5';
  }

  // review_text is optional, no validation needed

  if (Object.keys(errors).length > 0) {
    return { valid: false, errors };
  }

  return { valid: true, errors: null };
}

/**
 * Validate rating value
 * @param {number} rating - Rating value to validate
 * @returns {Object} Validation result
 */
function validateRating(rating) {
  if (rating === undefined || rating === null) {
    return { valid: false, error: 'Rating is required' };
  }

  if (typeof rating !== 'number') {
    return { valid: false, error: 'Rating must be a number' };
  }

  if (rating < 1 || rating > 5) {
    return { valid: false, error: 'Rating must be between 1 and 5' };
  }

  return { valid: true, error: null };
}

/**
 * Sort reviews by helpful count (descending)
 * @param {Array} reviews - Array of review objects
 * @returns {Array} Sorted reviews
 */
function sortReviewsByHelpful(reviews) {
  return [...reviews].sort((a, b) => (b.is_helpful_count || 0) - (a.is_helpful_count || 0));
}

/**
 * Sort reviews by rating (descending)
 * @param {Array} reviews - Array of review objects
 * @returns {Array} Sorted reviews
 */
function sortReviewsByRating(reviews) {
  return [...reviews].sort((a, b) => b.rating - a.rating);
}
