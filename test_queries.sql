SET search_path TO public;

SELECT * FROM film WHERE film_id = 42;

SELECT * FROM film WHERE release_year = 2006;

SELECT f.title, c.name
FROM film f
JOIN film_category fc ON fc.film_id = f.film_id
JOIN category c ON c.category_id = fc.category_id;

SELECT c.first_name, c.last_name, f.title
FROM rental r
JOIN inventory i ON i.inventory_id = r.inventory_id
JOIN film f ON f.film_id = i.film_id
JOIN customer c ON c.customer_id = r.customer_id
WHERE r.return_date IS NULL;

SELECT customer_id, COUNT(*)
FROM rental
GROUP BY customer_id
ORDER BY COUNT(*) DESC;

SELECT f.title, SUM(p.amount) AS revenue
FROM payment p
JOIN rental r ON r.rental_id = p.rental_id
JOIN inventory i ON i.inventory_id = r.inventory_id
JOIN film f ON f.film_id = i.film_id
GROUP BY f.title
ORDER BY revenue DESC;

SELECT * FROM rental
WHERE rental_date BETWEEN '2005-06-01' AND '2005-06-15';

SELECT * FROM payment
WHERE payment_date > '2005-08-01'
ORDER BY payment_date;

SELECT * FROM film WHERE length > 10;
