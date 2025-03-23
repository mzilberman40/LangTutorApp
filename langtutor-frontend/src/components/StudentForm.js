import React, { useState } from 'react';
import axios from 'axios';

const StudentForm = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    native_language: '',
    target_language: '',
    proficiency_level: 'A1'
  });

  const handleChange = e => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async e => {
    e.preventDefault();
    const token = localStorage.getItem('token');

    try {
      await axios.post(
        'http://127.0.0.1:8000/api/students/',
        formData,
        token ? { headers: { 'Authorization': `Bearer ${token}` } } : {}
      );
      alert('Student created successfully!');
    } catch (error) {
      console.error('Error details:', error.response?.data);
      alert('Error creating student.');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Create Student</h2>

      <input
        name="username"
        placeholder="Username"
        onChange={handleChange}
        required
      /><br />

      <input
        name="email"
        type="email"
        placeholder="Email"
        onChange={handleChange}
        required
      /><br />

      <input
        name="password"
        type="password"
        placeholder="Password"
        onChange={handleChange}
        required
      /><br />

      <input
        name="native_language"
        placeholder="Native Language"
        onChange={handleChange}
        required
      /><br />

      <input
        name="target_language"
        placeholder="Target Language"
        onChange={handleChange}
        required
      /><br />

      <select
        name="proficiency_level"
        onChange={handleChange}
        value={formData.proficiency_level}
      >
        <option value="A1">A1</option>
        <option value="A2">A2</option>
        <option value="B1">B1</option>
        <option value="B2">B2</option>
        <option value="C1">C1</option>
        <option value="C2">C2</option>
      </select><br />

      <button type="submit">Create Student</button>
    </form>
  );
};

export default StudentForm;

