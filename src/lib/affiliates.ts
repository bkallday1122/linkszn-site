// Public Associates tracking ID; this is not a credential.
export const AMAZON_ASSOCIATE_TAG = 'linksznn-20';

export function amazonProductUrl(asin: string): string {
  if (typeof asin !== 'string' || !/^[A-Z0-9]{10}$/.test(asin)) {
    throw new Error('amazon_asin must be a 10-character Amazon product identifier');
  }
  return `https://www.amazon.com/dp/${asin}?tag=${AMAZON_ASSOCIATE_TAG}`;
}
