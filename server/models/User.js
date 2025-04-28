/**
 * User model for in-memory storage
 * In a production environment, this would be replaced with a database model
 */
class User {
  constructor() {
    this.users = [];
    this.nextId = 1;
  }

  /**
   * Create a new user
   * @param {Object} userData - User data
   * @returns {Object} - Created user
   */
  create(userData) {
    const user = {
      id: this.nextId++,
      email: userData.email,
      password: userData.password, // This should be hashed before storage
      firstName: userData.firstName || '',
      lastName: userData.lastName || '',
      role: userData.role || 'patient',
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    this.users.push(user);
    return { ...user, password: undefined }; // Return user without password
  }

  /**
   * Find a user by email
   * @param {string} email - User email
   * @returns {Object|null} - User object or null if not found
   */
  findByEmail(email) {
    return this.users.find(user => user.email === email) || null;
  }

  /**
   * Find a user by ID
   * @param {number} id - User ID
   * @returns {Object|null} - User object or null if not found
   */
  findById(id) {
    return this.users.find(user => user.id === id) || null;
  }

  /**
   * Update a user
   * @param {number} id - User ID
   * @param {Object} userData - User data to update
   * @returns {Object|null} - Updated user or null if not found
   */
  update(id, userData) {
    const index = this.users.findIndex(user => user.id === id);
    
    if (index === -1) {
      return null;
    }
    
    const updatedUser = {
      ...this.users[index],
      ...userData,
      updatedAt: new Date()
    };
    
    this.users[index] = updatedUser;
    return { ...updatedUser, password: undefined }; // Return user without password
  }

  /**
   * Delete a user
   * @param {number} id - User ID
   * @returns {boolean} - True if user was deleted
   */
  delete(id) {
    const index = this.users.findIndex(user => user.id === id);
    
    if (index === -1) {
      return false;
    }
    
    this.users.splice(index, 1);
    return true;
  }
}

module.exports = new User();
