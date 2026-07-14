# Verify: engineering-cms

## must-pass

| # | Scenario | Input | Expected Platform |
|---|---------|-------|------------------|
| 1 | WordPress custom post type | "Create a custom post type for events" | wordpress-dev |
| 2 | Drupal module development | "Create a Drupal module for content moderation" | drupal-dev |
| 3 | WooCommerce payment | "Integrate Stripe in WooCommerce" | wordpress-ecom |
| 4 | Drupal Commerce | "Set up Drupal Commerce checkout" | drupal-ecom |
| 5 | WP performance | "Optimize WordPress Core Web Vitals" | wordpress-perf |
| 6 | Drupal performance | "Optimize Drupal cache tags" | drupal-perf |
| 7 | CMS selection | "Should we choose WordPress or Drupal?" | cms-arch |

## should-pass (>=4)

| # | Scenario | Expected |
|---|---------|----------|
| 8 | WP answer should use WP-specific APIs | Platform-specific knowledge |
| 9 | Drupal answer should reference Drupal concepts | Platform-specific knowledge |
| 10 | Mix of Gutenberg + custom code should exist | WP dev knowledge complete |

## must-not-fail

| # | Check |
|---|-------|
| 11 | Lost WooCommerce product architecture from wordpress-shopping-cart |
| 12 | Lost BigPipe/cache tag knowledge from drupal-performance |
