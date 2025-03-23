import React from 'react';
import StudentList from './components/StudentList'; // default export
import StudentForm from './components/StudentForm'; // default export
import Login from './components/Login'; // default export

function App() {
  return (
    <div className="App">
      <Login />
      <hr />
      <StudentForm />
      <hr />
      <StudentList />
    </div>
  );
}

export default App;
