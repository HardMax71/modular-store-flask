# Modular Store Flask

Modular Store Flask is a comprehensive, feature-rich e-commerce platform built with Flask. This project aims to provide 
a flexible and scalable solution for online stores, with a wide range of features to enhance both user experience and store management.

## Key Features

- **Product Catalog**: Robust product management with categories, search, and filtering options
- **Shopping Cart**: Seamless shopping experience with cart management and discount applications
- **User Management**: Secure user authentication, profiles, and order history
- **Order Processing**: Streamlined checkout process with multiple payment and shipping options
- **Admin Dashboard**: Comprehensive tools for product, order, and user management
- **Responsive Design**: Mobile-friendly interface for shopping on any device
- **Internationalization**: Support for multiple languages and currencies
- **Wishlist**: Allow users to save products for future purchase
- **Reviews and Ratings**: Enable customers to share their experiences and opinions
- **Personalized Recommendations**: Suggest products based on user behavior and preferences
- **Analytics and Reporting**: Gain insights into sales and user behavior
- **Security Features**: Implement best practices for e-commerce security




<details>
<summary>Getting Started</summary>

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/HardMax71/modular-store-flask.git
   cd modular-store-flask
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python app.py
   ```

Visit `http://localhost:5000` in your browser to see the application running.

</details>

<details>
<summary>Current state of things</summary>

| Feature Category               | Feature Idea                                                                                                                                                                                                                                                                                                                                                                        | Status                               |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| Product Catalog                | * Display products with images, prices, and other relevant information<br> * Implement product categories and subcategories for better organization<br> * Allow users to search for products based on keywords, categories, or tags<br> * Implement product filtering and sorting options<br> * Display related products or product recommendations                                 | ✅ Done                               |
| Product Details                | * Create a detailed product page with all relevant information<br> * Display product variants (e.g., size, color) and allow users to select them<br> * Show product reviews and ratings from other users<br> * Implement a product rating system for users to rate products<br> * Allow users to add products to their wishlist                                                     | ✅ Done                               |
| Shopping Cart                  | * Allow users to add products to their shopping cart<br> * Display the total price and number of items in the cart<br> * Provide options to update quantities or remove items from the cart<br> * Implement a mini-cart or quick view of the cart contents<br> * Allow users to apply discount codes or promotional offers                                                          | ✅ Done                               |
| Checkout Process               | * Implement a multi-step checkout process (e.g., shipping address, billing information, order summary)<br> * Allow users to select a shipping address or add a new one<br> * Provide options for different shipping methods and calculate shipping costs<br> * Integrate with a payment gateway for secure online payments<br> * Display order confirmation and send email receipts | ✅ Done                               |
| Order Management               | * Implement an order tracking system for users to view their order status<br> * Allow users to view their order history and details<br> * Provide options for users to cancel or modify orders (if applicable)<br> * Send email notifications for order updates and shipping information                                                                                            | ✅ Done                               |
| User Reviews and Ratings       | * Allow users to write reviews and rate products they have purchased<br> * Display user reviews and ratings on product pages<br> * Implement a moderation system for reviewing and approving user-generated content<br> * Provide options for users to report inappropriate reviews or ratings                                                                                      | ✅ Done                               |
| Wishlist Functionality         | * Allow users to add products to their wishlist<br> * Provide options to manage wishlist items (remove, add to cart)<br> * Send email notifications or reminders for wishlist items on sale or back in stock                                                                                                                                                                        | ✅ Done                               |
| Discounts and Promotions       | * Implement a discount code system for promotional offers<br> * Apply discounts automatically during the checkout process<br> * Display promotional banners or popups for ongoing sales or special offers<br> * Send email notifications for personalized discounts or limited-time offers                                                                                          | ✅ Done                               |
| Notifications and Alerts       | * Implement a notification system for users (e.g., order updates, product back in stock)<br> * Allow users to manage their notification preferences<br> * Send email alerts for important events or updates                                                                                                                                                                         | ✅ Done                               |
| Product Inventory Management   | * Track product inventory levels and update them in real-time<br> * Implement low stock alerts or notifications for admin users<br> * Provide options to mark products as out of stock or discontinued                                                                                                                                                                              | ✅ Done                               |
| Analytics and Reporting        | * Implement analytics tracking for user behavior and sales data<br> * Generate reports for sales, revenue, and product performance<br> * Provide insights and metrics for marketing and business decisions                                                                                                                                                                          | ✅ Done                               |
| Search and Autocomplete        | * Implement a search functionality for users to find products easily<br> * Provide autocomplete suggestions based on user input<br> * Optimize search results based on relevance and popularity                                                                                                                                                                                     | ✅ Done                               |
| Product Comparison             | * Allow users to compare multiple products side by side<br> * Display key features, specifications, and prices for easy comparison<br> * Provide options to add compared products to the cart or wishlist                                                                                                                                                                           | ✅ Done                               |
| Social Sharing and Integration | * Implement social sharing buttons for products and pages<br> * Allow users to login or register using their social media accounts<br> * Integrate with social media platforms for product promotion and user engagement                                                                                                                                                            | ✅ Done                               |
| Customer Support and Live Chat | * Implement a customer support ticketing system<br> * Provide live chat functionality for real-time assistance<br> * Offer self-service options like FAQs or knowledge base articles                                                                                                                                                                                                | FAQ - done; Ticketing system - done; |
| Mobile Optimization and Design | * Ensure the web store is fully responsive and mobile-friendly<br> * Optimize images and assets for faster loading on mobile devices<br> * Implement mobile-specific features like swipe gestures or mobile payments                                                                                                                                                                |                                      |
| Internationalization           | * Support multiple languages and currencies for a global audience<br> * Implement geolocation to detect user's location and adapt the store accordingly<br> * Provide options for users to switch languages or currencies                                                                                                                                                           | ✅ Done                               |
| Personalization and Recs       | * Implement personalized product recommendations based on user behavior<br> * Display recently viewed or related products for each user<br> * Send personalized email campaigns or newsletters based on user preferences                                                                                                                                                            | ✅ Done \[except sending mails\]      |
| Security and Privacy           | * Implement secure user authentication and authorization<br> * Protect user data and transactions with encryption and secure protocols<br> * Comply with relevant privacy regulations (e.g., GDPR, CCPA)<br> * Regularly update and patch software to address security vulnerabilities                                                                                              | ✅ Done \[except GDPR stuff\]         |
| Performance Optimization       | * Optimize website speed and performance for better user experience<br> * Implement caching mechanisms for faster page loading<br> * Minimize the use of third-party scripts or plugins that may slow down the site<br> * Regularly monitor and optimize database queries for improved performance                                                                                  |                                      |
| Accessibility                  | * Ensure the web store is accessible to users with disabilities<br> * Follow web accessibility guidelines (e.g., WCAG) for inclusive design<br> * Provide alternative text for images and proper labeling for form elements<br> * Test the store for compatibility with assistive technologies                                                                                      |                                      |
| Testing and Quality Assurance  | * Implement a comprehensive testing strategy for the web store<br> * Conduct functional testing, usability testing, and performance testing<br> * Perform cross-browser and cross-device testing for compatibility<br> * Establish a quality assurance process to identify and fix bugs or issues                                                                                   |                                      |
| Backup and Disaster Recovery   | * Implement regular data backups to prevent data loss<br> * Develop a disaster recovery plan for unexpected events or system failures<br> * Test the backup and recovery processes periodically to ensure their effectiveness                                                                                                                                                       | ✅ Done                               |


</details>

## Project Structure

```
modular-store-flask/
│
├── app.py                 # Main application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Project dependencies
|
├── README.md              # Project overview and instructions
├── LICENSE.md             # License information
├── .gitignore             # Files and directories to ignore in Git
│
├── forms/                 # Form classes for user input validation
│
├── instance/              # contains single file - data.db (SQLite database)
│
├── modules/               # Application modules
│   ├── admin/             # Admin-related functionality
│   ├── auth/              # Authentication module
│   ├── carts/             # Shopping cart functionality
│   ├── compare/           # Product comparison feature
│   ├── db/                # Database models and operations
│   ├── error_handlers/    # Error handling module
│   ├── filter/            # Product filtering functionality
│   ├── main/              # Main routes and views
│   ├── profile/           # User profile management
│   ├── purchase_history/  # Order history and tracking
│   ├── recommendations/   # Product recommendation system
│   ├── reviews/           # Product review functionality
│   ├── tickets/           # Customer support ticket system
│   ├── wishlists/         # Wishlist functionality
│   └── ... (single .py files for other features, like caching, logging, ..)
│
├── static/                # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   ├── img/
│   └── robots.txt        # Robots file for search engine indexing
│
├── templates/             # HTML templates
│   ├── admin/
│   ├── auth/
│   ├── cart/
│   ├── error/
│   └── tickets/
│
├── translations/          # Internationalization files
│
└── tests/                 # TODO: Unit and integration tests
    ├── unit/
    └── integration/
```

This structure represents the main components of the Modular Store Flask project:

- `app.py`: The main entry point of the application.
- `config.py`: Contains configuration settings for different environments.
- `modules/`: Houses the different functional modules of the application.
- `static/`: Contains all static files like CSS, JavaScript, and images.
- `templates/`: Holds all the HTML templates used in the application.
- `translations/`: Contains files for internationalization support.
- `instance/`: Stores instance-specific configurations (not version controlled).
- `tests/`: Contains all the unit and integration tests for the project.

Each module in the `modules/` directory typically contains its own views, forms, and utility functions, 
promoting a modular and maintainable code structure.

## Database Schema

![Database Schema](diagrams/plantuml_erd.png)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.



